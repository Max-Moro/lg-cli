from __future__ import annotations

from pathlib import Path

from lg.manifest.builder import build_manifest
from lg.types import ContextSpec, SectionRef
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

    # адресная секция: self lg-cfg
    cfg_root = (tmp_path / "lg-cfg").resolve()
    spec = ContextSpec(
        kind="section",
        name="all",
        section_refs=[SectionRef(cfg_root=cfg_root, name="all", multiplicity=1)],
    )

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

    cfg_root = (tmp_path / "lg-cfg").resolve()
    spec = ContextSpec(
        kind="section",
        name="all",
        section_refs=[SectionRef(cfg_root=cfg_root, name="all", multiplicity=1)],
    )

    # фейковый VCS: изменён только один файл
    class FakeVcs:
        def changed_files(self, root: Path):
            return {"src/changed.py"}

    mf = build_manifest(root=tmp_path, spec=spec, mode="changes", vcs=FakeVcs())
    paths = [fr.rel_path for fr in mf.files]
    assert paths == ["src/changed.py"]
