"""
Tests for trivial file detection in Java adapter.
"""

from pathlib import Path

from lg.adapters.langs.java import JavaCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial package-info.java via should_skip()."""
    adapter = make_adapter(JavaCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/package-info.java"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial package-info.java."""
    adapter = make_adapter(JavaCfg())

    ctx = lctx(do_non_trivial, Path("/src/com/example/utils/package-info.java"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Java files."""
    adapter = make_adapter(JavaCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/Utils.java"))
    assert adapter.should_skip(ctx) is False
