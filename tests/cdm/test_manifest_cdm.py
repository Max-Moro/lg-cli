from __future__ import annotations

import io
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from lg.filtering.manifest import build_section_manifest
from lg.template.context import TemplateContext
from lg.addressing.types import ResolvedSection
from lg.section import SectionLocation
from lg.git import VcsProvider
from tests.infrastructure.file_utils import write
from tests.infrastructure import load_sections
from .conftest import mk_run_ctx


class FakeVcs(VcsProvider):
    def __init__(self, changed: set[str]) -> None:
        self._changed = set(changed)
    def changed_files(self, root: Path) -> set[str]:
        return set(self._changed)


def _build_section_manifest(
    root: Path,
    section_name: str,
    scope_rel: str = "",
    *,
    vcs_mode: str = "all",
    vcs=None
):
    """
    Helper to build manifest for a single section in the new V2 pipeline.

    Args:
        root: Repository root
        section_name: Section name
        scope_rel: Relative path to scope (empty for root)
        vcs_mode: VCS mode ("all" or "changes")
        vcs: VCS provider

    Returns:
        SectionManifest for the specified section
    """
    rc = mk_run_ctx(root)
    template_ctx = TemplateContext(rc)

    # Determine scope_dir based on scope_rel
    if scope_rel:
        scope_dir = (root / scope_rel).resolve()
    else:
        scope_dir = root

    sections = load_sections(scope_dir)
    section_cfg = sections.get(section_name)

    if not section_cfg:
        available = list(sections.keys())
        raise RuntimeError(
            f"Section '{section_name}' not found in {scope_dir}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    resolved = ResolvedSection(
        scope_dir=scope_dir,
        scope_rel=scope_rel,
        location=SectionLocation(file_path=Path("test"), local_name=section_name),
        section_config=section_cfg,
        name=section_name
    )

    return build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=root,
        vcs=vcs or rc.vcs,
        gitignore_service=rc.gitignore,
        vcs_mode=vcs_mode
    )

def test_scope_and_filters_limit_to_scope(monorepo: Path):
    """
    Section packages/svc-a::a should only see its own scope (packages/svc-a/**) and
    filter files by allow:
      - /src/**, /README.md
    Nothing from apps/web/** should be included.
    """
    # Test section 'a' from scope 'packages/svc-a'
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")
    rels = [f.rel_path for f in manifest.files]

    # Files from own scope and matching allow
    assert "packages/svc-a/src/pkg/x.py" in rels
    assert "packages/svc-a/src/other/y.py" in rels
    assert "packages/svc-a/README.md" in rels

    # Nothing from different scope
    assert all(not p.startswith("apps/web/") for p in rels)

    # Verify that the section correctly determined its scope
    assert manifest.ref.scope_rel == "packages/svc-a"
    assert manifest.ref.name == "a"


def test_targets_match_are_relative_to_scope(monorepo: Path):
    """
    In a.sec.yaml there is targets.match: '/src/pkg/**.py' → should apply only to
    packages/svc-a/src/pkg/x.py, but not to src/other/y.py.
    """
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")

    # Map rel_path -> overrides for python
    overrides = {
        f.rel_path: (f.adapter_overrides.get("python") or {})
        for f in manifest.files
    }

    assert overrides.get("packages/svc-a/src/pkg/x.py").get("strip_function_bodies") is True

    # Find file src/other/y.py
    other_file = next((f for f in manifest.files if f.rel_path == "packages/svc-a/src/other/y.py"), None)
    assert other_file is not None
    assert "python" not in other_file.adapter_overrides


def test_changes_mode_filters_by_vcs_and_scope(monorepo: Path):
    """
    In changes-mode only changed files should be included AND within the scope.
    """
    changed = {
        "packages/svc-a/src/only_this.py",      # will be included (create file)
        "apps/web/docs/index.md",               # different scope — not in this section
        "packages/svc-a/README.md",             # will be included if changed
    }

    # Create missing file from changed
    write(monorepo / "packages" / "svc-a" / "src" / "only_this.py", "print('changed')\n")

    manifest = _build_section_manifest(
        monorepo, "a", "packages/svc-a",
        vcs_mode="changes",
        vcs=FakeVcs(changed)
    )
    rels = [f.rel_path for f in manifest.files]

    assert "packages/svc-a/src/only_this.py" in rels
    assert "packages/svc-a/README.md" in rels
    # index.md from apps/web is changed, but different scope → won't appear in this section
    assert "apps/web/docs/index.md" not in rels


def test_empty_policy_include_allows_empty_files(monorepo: Path):
    """
    If python.empty_policy: include is set in section, empty .py files won't be filtered.
    """
    # 1) Add empty_policy to section a → for python adapter
    sec_path = monorepo / "packages" / "svc-a" / "lg-cfg" / "a.sec.yaml"
    y = YAML()
    data = y.load(sec_path.read_text(encoding="utf-8")) or {}
    a = data.setdefault("a", {})
    py = a.setdefault("python", {})
    py["empty_policy"] = "include"
    # Rewrite YAML (to preserve readable format)
    buf = io.StringIO()
    y.dump(data, buf)
    sec_path.write_text(buf.getvalue(), encoding="utf-8")

    # 2) Create empty file in allow-zone
    empty_fp = monorepo / "packages" / "svc-a" / "src" / "pkg" / "empty.py"
    empty_fp.parent.mkdir(parents=True, exist_ok=True)
    empty_fp.write_bytes(b"")

    # 3) Build manifest and verify empty file is included
    manifest = _build_section_manifest(monorepo, "a", "packages/svc-a")
    rels = [f.rel_path for f in manifest.files]
    assert "packages/svc-a/src/pkg/empty.py" in rels


def test_missing_sections_diagnostic_includes_available(monorepo: Path):
    """
    If a non-existent section is requested in child scope, build_section_manifest should
    fail with a message:
      - indicating scope: apps/web/...
      - listing available sections in this scope
    """
    # Test attempt to get non-existent section 'missing' from scope 'apps/web'
    with pytest.raises(RuntimeError) as ei:
        _build_section_manifest(monorepo, "missing", "apps/web")

    msg = str(ei.value)
    assert "not found" in msg
    assert "apps" in msg and "web" in msg
    assert "Available:" in msg
    # In our fixture apps/web has 'web-api'
    assert "web-api" in msg
