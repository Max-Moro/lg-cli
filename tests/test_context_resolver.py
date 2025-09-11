from pathlib import Path

import pytest

from lg.cache.fs_cache import Cache
from lg.config.paths import cfg_root
from lg.context import list_contexts, resolve_context
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.vcs import NullVcs


def _ctx(root: Path):
    return RunContext(root=root, options=RunOptions(), cache=Cache(root, tool_version="0.0.0"), vcs=NullVcs(), tokenizer=default_tokenizer())

def _as_counts(spec):
    """Вспомогательно: свернуть section_refs → {ph: multiplicity} и проверить cfg_root=tmpproj/lg-cfg."""
    # spec.section_refs — список SectionRef(cfg_root, name, ph, multiplicity)
    counts = {}
    for r in spec.section_refs:
        counts[r.ph] = counts.get(r.ph, 0) + r.multiplicity
    return counts

def test_list_contexts(tmpproj: Path):
    assert list_contexts(tmpproj) == ["a", "b"]

def test_resolve_ctx_explicit(tmpproj: Path):
    spec = resolve_context("ctx:a", _ctx(tmpproj))
    assert spec.kind == "context"
    assert spec.name == "a"
    assert _as_counts(spec) == {"docs": 1}
    base = cfg_root(tmpproj).resolve()
    assert all(r.cfg_root.resolve() == base for r in spec.section_refs)

def test_resolve_section_explicit(tmpproj: Path):
    spec = resolve_context("sec:all", _ctx(tmpproj))
    assert spec.kind == "section"
    assert _as_counts(spec) == {"all": 1}
    base = cfg_root(tmpproj).resolve()
    assert all(r.cfg_root.resolve() == base for r in spec.section_refs)

def test_resolve_auto_ctx_then_sec(tmpproj: Path):
    # "a" существует как контекст
    spec = resolve_context("a", _ctx(tmpproj))
    assert spec.kind == "context"
    # "docs" не существует как контекст — берём секцию
    spec2 = resolve_context("docs", _ctx(tmpproj))
    assert spec2.kind == "section"
    assert _as_counts(spec2) == {"docs": 1}
    base = cfg_root(tmpproj).resolve()
    assert all(r.cfg_root.resolve() == base for r in spec2.section_refs)

def test_resolve_nested_and_counts(tmpproj: Path):
    # b.tpl.md включает tpl:a (где docs) + секцию all
    spec = resolve_context("ctx:b", _ctx(tmpproj))
    assert _as_counts(spec) == {"docs": 1, "all": 1}
    base = cfg_root(tmpproj).resolve()
    assert all(r.cfg_root.resolve() == base for r in spec.section_refs)

def test_missing_context(tmpproj: Path):
    with pytest.raises(RuntimeError):
        resolve_context("ctx:missing", _ctx(tmpproj))
