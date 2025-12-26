"""
Tests for trivial file detection in Kotlin adapter.
"""

from pathlib import Path

from lg.adapters.langs.kotlin import KotlinCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial package-only file via should_skip()."""
    adapter = make_adapter(KotlinCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/package.kt"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip file with function."""
    adapter = make_adapter(KotlinCfg())

    ctx = lctx(do_non_trivial, Path("/src/com/example/utils/package.kt"))
    assert adapter.should_skip(ctx) is False


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Kotlin files."""
    adapter = make_adapter(KotlinCfg())

    ctx = lctx(do_trivial, Path("/src/com/example/utils/Utils.kt"))
    assert adapter.should_skip(ctx) is False
