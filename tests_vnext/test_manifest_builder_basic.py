from __future__ import annotations

from pathlib import Path

from lg_vnext.config.model import Config, SectionCfg, FilterNode
from lg_vnext.manifest.builder import build_manifest
from lg_vnext.types import ContextSpec, SectionUsage
from lg_vnext.vcs import NullVcs


def _write(tmp: Path, rel: str, text: str = "x") -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_manifest_all_mode_with_gitignore_and_filters(tmp_path: Path):
    # файловая структура
    _write(tmp_path, "src/a.py")
    _write(tmp_path, "src/b.md")
    _write(tmp_path, "ignore/me.py")
    (tmp_path / ".gitignore").write_text("ignore/\n", encoding="utf-8")

    # конфиг секции: .py и .md, запрещаем всё, кроме src/**
    sec = SectionCfg(
        extensions=[".py", ".md"],
        code_fence=True,
        filters=FilterNode(mode="allow", allow=["/src/**"])
    )
    cfg = Config(sections={"all": sec})

    spec = ContextSpec(kind="section", name="all", sections=SectionUsage(by_name={"all": 1}))

    mf = build_manifest(root=tmp_path, spec=spec, sections_cfg=cfg.sections, mode="all", vcs=NullVcs())
    paths = [fr.rel_path for fr in mf.files]
    assert "src/a.py" in paths
    assert "src/b.md" in paths
    assert "ignore/me.py" not in paths


def test_manifest_changes_mode(tmp_path: Path, monkeypatch):
    # файлы
    _write(tmp_path, "src/changed.py")
    _write(tmp_path, "src/untouched.py")
    sec = SectionCfg(extensions=[".py"], code_fence=True, filters=FilterNode(mode="block"))

    cfg = Config(sections={"all": sec})
    spec = ContextSpec(kind="section", name="all", sections=SectionUsage(by_name={"all": 1}))

    # фейковый VCS, помечаем только один файл как изменённый
    class FakeVcs:
        def changed_files(self, root: Path):
            return {"src/changed.py"}

    mf = build_manifest(root=tmp_path, spec=spec, sections_cfg=cfg.sections, mode="changes", vcs=FakeVcs())
    paths = [fr.rel_path for fr in mf.files]
    assert paths == ["src/changed.py"]
