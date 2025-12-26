"""
Tests for trivial file detection in Scala adapter.
"""

from pathlib import Path

from lg.adapters.langs.scala import ScalaCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial package.scala via should_skip()."""
    adapter = make_adapter(ScalaCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/package.scala"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial package.scala."""
    adapter = make_adapter(ScalaCfg())

    ctx = lctx(do_non_trivial, Path("/src/com/example/utils/package.scala"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Scala files."""
    adapter = make_adapter(ScalaCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/Utils.scala"))
    assert adapter.should_skip(ctx) is False
