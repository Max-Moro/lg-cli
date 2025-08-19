from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.config import load_config
from lg.context.resolver import resolve_context, list_contexts
from lg.engine import RunContext
from lg.types import RunOptions
from lg.vcs import NullVcs


def _ctx(root: Path):
    return RunContext(root=root, config=load_config(root), options=RunOptions(),
                      cache=Cache(root, tool_version="0.0.0"), vcs=NullVcs())

def test_list_contexts(tmpproj: Path):
    assert list_contexts(tmpproj) == ["a", "b"]

def test_resolve_ctx_explicit(tmpproj: Path):
    spec = resolve_context("ctx:a", _ctx(tmpproj))
    assert spec.kind == "context"
    assert spec.name == "a"
    assert spec.sections.by_name == {"docs": 1}

def test_resolve_section_explicit(tmpproj: Path):
    spec = resolve_context("sec:all", _ctx(tmpproj))
    assert spec.kind == "section"
    assert spec.sections.by_name == {"all": 1}

def test_resolve_auto_ctx_then_sec(tmpproj: Path):
    # "a" существует как контекст
    spec = resolve_context("a", _ctx(tmpproj))
    assert spec.kind == "context"
    # "docs" не существует как контекст — берём секцию
    spec2 = resolve_context("docs", _ctx(tmpproj))
    assert spec2.kind == "section"
    assert spec2.sections.by_name == {"docs": 1}

def test_resolve_nested_and_counts(tmpproj: Path):
    # b.tpl.md включает tpl:a (где docs) + секцию all
    spec = resolve_context("ctx:b", _ctx(tmpproj))
    assert spec.sections.by_name == {"docs": 1, "all": 1}

def test_cycle_detection(tmpproj: Path):
    # создаём цикл: a → tpl:b, b уже ссылается на a
    (tmpproj / "lg-cfg" / "contexts" / "a.tpl.md").write_text("${tpl:b}\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        resolve_context("ctx:a", _ctx(tmpproj))

def test_missing_section(tmpproj: Path):
    with pytest.raises(RuntimeError):
        resolve_context("sec:missing", _ctx(tmpproj))

def test_missing_context(tmpproj: Path):
    with pytest.raises(RuntimeError):
        resolve_context("ctx:missing", _ctx(tmpproj))
