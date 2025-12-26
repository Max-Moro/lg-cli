"""
Tests for trivial file detection in Python adapter.
"""

from pathlib import Path

from lg.adapters.langs.python import PythonCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial __init__.py via should_skip()."""
    adapter = make_adapter(PythonCfg())

    ctx = lctx(do_trivial, Path("/pkg/__init__.py"))
    assert adapter.should_skip(ctx) is True

def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial __init__.py."""
    adapter = make_adapter(PythonCfg())

    ctx = lctx(do_non_trivial, Path("/pkg/__init__.py"))
    assert adapter.should_skip(ctx) is False

def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Python files."""
    adapter = make_adapter(PythonCfg())

    ctx = lctx(do_trivial, Path("/pkg/module.py"))
    assert adapter.should_skip(ctx) is False
