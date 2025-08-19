from pathlib import Path
import pytest

from lg.config import load_config
from lg.cache.fs_cache import Cache
from lg.context.resolver import resolve_context
from lg.context.composer import compose_context
from lg.types import RunOptions
from lg.engine import RunContext
from lg.vcs import NullVcs

def _write_ctx(root: Path, rel: str, body: str):
    p = root / "lg-cfg" / "contexts" / f"{rel}.tpl.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")

def _mk_ctx(root: Path) -> RunContext:
    return RunContext(
        root=root.resolve(),
        config=load_config(root),
        options=RunOptions(),
        cache=Cache(root, tool_version="0.0.0"),
        vcs=NullVcs(),
    )

def test_context_nested_ok(tmp_path: Path, monkeypatch):
    # Минимальный конфиг с секцией "sec"
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        "schema_version: 6\nsec:\n  extensions: ['.md']\n  code_fence: false\n",
        encoding="utf-8",
    )
    # Шаблоны: root → tpl:mid/inner → tpl:leaf; leaf содержит секцию sec
    _write_ctx(tmp_path, "leaf", "LEAF ${sec}")
    _write_ctx(tmp_path, "mid/inner", "MIDDLE\n${tpl:leaf}\n")
    _write_ctx(tmp_path, "root", "ROOT\n${tpl:mid/inner}\n")

    run_ctx = _mk_ctx(tmp_path)

    # Резолвим контекст (строит AST и считает кратности секций)
    spec = resolve_context("ctx:root", run_ctx)
    assert spec.kind == "context"
    assert spec.sections.by_name == {"sec": 1}

    # Подкладываем готовый рендер секции "sec" как будто его собрали ранее
    rendered_by_section = {"sec": "LISTING[sec]\n"}

    # Компонуем финальный документ
    composed = compose_context(tmp_path, spec, rendered_by_section)
    out = composed.text

    assert "ROOT" in out
    assert "MIDDLE" in out
    assert "LEAF LISTING[sec]" in out  # секция вставилась на место плейсхолдера

def test_context_cycle_detection(tmp_path: Path):
    # Конфиг (любая секция, чтобы загрузка прошла)
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        "schema_version: 6\nx:\n  extensions: ['.md']\n",
        encoding="utf-8",
    )
    # Циклические шаблоны
    _write_ctx(tmp_path, "a", "A -> ${tpl:b}")
    _write_ctx(tmp_path, "b", "B -> ${tpl:a}")

    run_ctx = RunContext(
        root=tmp_path.resolve(),
        config=load_config(tmp_path),
        options=RunOptions(),
        cache=Cache(tmp_path, tool_version="0.0.0"),
        vcs=NullVcs(),
    )

    with pytest.raises(RuntimeError) as ei:
        resolve_context("ctx:a", run_ctx)
    assert "cycle detected" in str(ei.value).lower()
