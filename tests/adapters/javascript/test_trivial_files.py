"""
Tests for trivial file detection in JavaScript adapter.
"""

from pathlib import Path

from lg.adapters.langs.javascript import JavaScriptCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial index.js via should_skip()."""
    adapter = make_adapter(JavaScriptCfg())

    ctx = lctx(do_trivial, Path("/src/components/index.js"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial index.js."""
    adapter = make_adapter(JavaScriptCfg())

    ctx = lctx(do_non_trivial, Path("/src/components/index.js"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular JavaScript files."""
    adapter = make_adapter(JavaScriptCfg())

    ctx = lctx(do_trivial, Path("/src/components/Button.js"))
    assert adapter.should_skip(ctx) is False
