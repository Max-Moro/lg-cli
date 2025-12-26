"""
Tests for trivial file detection in Go adapter.
"""

from pathlib import Path

from lg.adapters.langs.go import GoCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial doc.go via should_skip()."""
    adapter = make_adapter(GoCfg())

    ctx = lctx(do_trivial, Path("/pkg/utils/doc.go"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial doc.go."""
    adapter = make_adapter(GoCfg())

    ctx = lctx(do_non_trivial, Path("/pkg/utils/doc.go"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Go files."""
    adapter = make_adapter(GoCfg())

    ctx = lctx(do_trivial, Path("/pkg/utils/utils.go"))
    assert adapter.should_skip(ctx) is False
