from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.config.paths import cfg_root
from lg.context import resolve_context, compose_context
from lg.run_context import RunContext
from lg.types import RunOptions
from lg.vcs import NullVcs


def _write_tpl(root: Path, rel: str, body: str):
    """Создаёт шаблон .tpl.md в lg-cfg/ (с поддиректорией при необходимости)."""
    p = root / "lg-cfg" / f"{rel}.tpl.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")

def _write_ctx(root: Path, rel: str, body: str):
    """Создаёт контекст .ctx.md в lg-cfg/."""
    p = root / "lg-cfg" / f"{rel}.ctx.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")

def _mk_ctx(root: Path) -> RunContext:
    return RunContext(
        root=root.resolve(),
        options=RunOptions(),
        cache=Cache(root, tool_version="0.0.0"),
        vcs=NullVcs(),
    )

def test_context_nested_ok(tmp_path: Path, monkeypatch):
    # Минимальный конфиг с секцией "sec" по новой схеме (sections.yaml)
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        "schema_version: 6\nsec:\n  extensions: ['.md']\n  code_fence: false\n",
        encoding="utf-8",
    )
    # Тemplating: root.ctx.md → ${tpl:mid/inner} → mid/inner.tpl.md → ${tpl:leaf}
    # leaf.tpl.md содержит секцию ${sec}
    _write_tpl(tmp_path, "leaf", "LEAF ${sec}")
    _write_tpl(tmp_path, "mid/inner", "MIDDLE\n${tpl:leaf}\n")
    _write_ctx(tmp_path, "root", "ROOT\n${tpl:mid/inner}\n")

    run_ctx = _mk_ctx(tmp_path)

    # Резолвим контекст (строит AST и считает кратности секций)
    spec = resolve_context("ctx:root", run_ctx)
    assert spec.kind == "context"
    assert len(spec.section_refs) == 1
    ref = spec.section_refs[0]
    assert ref.name == "sec"
    assert ref.multiplicity == 1
    assert ref.cfg_root == cfg_root(tmp_path)

    # Подкладываем готовый рендер секции "sec" как будто его собрали ранее
    assert ref.canon is not None
    rendered_by_section = {ref.canon.as_key(): "LISTING[sec]\n"}

    # Компонуем финальный документ
    composed = compose_context(
        tmp_path,
        cfg_root(tmp_path),
        spec,
        rendered_by_section,
        ph2canon=spec.ph2canon,
    )
    out = composed.text

    assert "ROOT" in out
    assert "MIDDLE" in out
    assert "LEAF LISTING[sec]" in out  # секция вставилась на место плейсхолдера

def test_context_cycle_detection(tmp_path: Path):
    # Конфиг (любая секция, чтобы загрузка прошла)
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        "schema_version: 6\nx:\n  extensions: ['.md']\n",
        encoding="utf-8",
    )
    # Цикл через шаблоны: a.tpl.md -> ${tpl:b}, b.tpl.md -> ${tpl:a}, контекст указывает на один из них
    _write_tpl(tmp_path, "a", "A -> ${tpl:b}")
    _write_tpl(tmp_path, "b", "B -> ${tpl:a}")
    _write_ctx(tmp_path, "a", "${tpl:a}")  # корневой контекст, откуда начнётся разворачивание

    run_ctx = RunContext(
        root=tmp_path.resolve(),
        options=RunOptions(),
        cache=Cache(tmp_path, tool_version="0.0.0"),
        vcs=NullVcs(),
    )

    with pytest.raises(RuntimeError) as ei:
        resolve_context("ctx:a", run_ctx)
    assert "cycle detected" in str(ei.value).lower()
