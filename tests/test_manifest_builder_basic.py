from __future__ import annotations

from pathlib import Path

from lg.manifest.builder import build_manifest
from lg.types import ContextSpec, SectionRef, CanonSectionId
from lg.vcs import NullVcs


def _write(tmp: Path, rel: str, text: str = "x") -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _write_sections_yaml(tmp: Path, text: str) -> Path:
    p = tmp / "lg-cfg" / "sections.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def mk_local_sec_spec(repo_root: Path, sec_name: str) -> ContextSpec:
    """
    Формирует ContextSpec для секции текущего (self) lg-cfg,
    сразу проставляя корректный canon.
    """
    cfg_root = (repo_root / "lg-cfg").resolve()
    scope_dir = cfg_root.parent.resolve()
    try:
        scope_rel = scope_dir.relative_to(repo_root.resolve()).as_posix()
    except Exception:
        scope_rel = ""
    canon = CanonSectionId(scope_rel=scope_rel if scope_rel != "." else "", name=sec_name)
    ref = SectionRef(cfg_root=cfg_root, name=sec_name, ph=sec_name, multiplicity=1, canon=canon)
    return ContextSpec(kind="section", name=sec_name, section_refs=[ref])


def test_manifest_all_mode_with_gitignore_and_filters(tmp_path: Path):
    # файловая структура
    _write(tmp_path, "src/a.py")
    _write(tmp_path, "src/b.md")
    _write(tmp_path, "ignore/me.py")
    (tmp_path / ".gitignore").write_text("ignore/\n", encoding="utf-8")

    # секции в YAML: .py и .md, разрешаем только src/**
    _write_sections_yaml(
        tmp_path,
        """
schema_version: 6
all:
  extensions: [".py", ".md"]
  code_fence: true
  filters:
    mode: allow
    allow:
      - "/src/**"
""".lstrip(),
    )

    # адресная секция: self lg-cfg с корректным canon
    spec = mk_local_sec_spec(tmp_path, "all")

    mf = build_manifest(root=tmp_path, spec=spec, mode="all", vcs=NullVcs())
    paths = [fr.rel_path for fr in mf.files]
    assert "src/a.py" in paths
    assert "src/b.md" in paths
    assert "ignore/me.py" not in paths


def test_manifest_changes_mode(tmp_path: Path):
    # файлы
    _write(tmp_path, "src/changed.py")
    _write(tmp_path, "src/untouched.py")

    # секции в YAML: .py, default-allow (mode: block без block-правил)
    _write_sections_yaml(
        tmp_path,
        """
schema_version: 6
all:
  extensions: [".py"]
  code_fence: true
  filters:
    mode: block
""".lstrip(),
    )

    spec = mk_local_sec_spec(tmp_path, "all")

    # фейковый VCS: изменён только один файл
    class FakeVcs:
        def changed_files(self, root: Path):
            return {"src/changed.py"}

    mf = build_manifest(root=tmp_path, spec=spec, mode="changes", vcs=FakeVcs())
    paths = [fr.rel_path for fr in mf.files]
    assert paths == ["src/changed.py"]
