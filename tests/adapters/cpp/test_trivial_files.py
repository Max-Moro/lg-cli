"""
Tests for trivial file detection in C++ adapter.
"""

from pathlib import Path

from lg.adapters.langs.cpp import CppCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial forward-declaration header."""
    adapter = make_adapter(CppCfg())

    ctx = lctx(do_trivial, Path("/include/utils.hpp"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip header with class definitions."""
    adapter = make_adapter(CppCfg())

    ctx = lctx(do_non_trivial, Path("/include/utils.hpp"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_source_file(do_trivial):
    """Adapter should NOT skip .cpp source files."""
    adapter = make_adapter(CppCfg())

    ctx = lctx(do_trivial, Path("/src/utils.cpp"))
    assert adapter.should_skip(ctx) is False
