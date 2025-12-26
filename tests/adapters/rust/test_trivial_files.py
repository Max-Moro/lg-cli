"""
Tests for trivial file detection in Rust adapter.
"""

from pathlib import Path

from lg.adapters.langs.rust import RustCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial mod.rs via should_skip()."""
    adapter = make_adapter(RustCfg())

    ctx = lctx(do_trivial, Path("/src/utils/mod.rs"))
    assert adapter.should_skip(ctx) is True


def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial mod.rs."""
    adapter = make_adapter(RustCfg())

    ctx = lctx(do_non_trivial, Path("/src/utils/mod.rs"))
    assert adapter.should_skip(ctx) is False


def test_lib_rs_trivial(do_trivial):
    """Adapter should skip trivial lib.rs via should_skip()."""
    adapter = make_adapter(RustCfg())

    ctx = lctx(do_trivial, Path("/src/lib.rs"))
    assert adapter.should_skip(ctx) is True


def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular Rust files."""
    adapter = make_adapter(RustCfg())

    ctx = lctx(do_trivial, Path("/src/utils/helpers.rs"))
    assert adapter.should_skip(ctx) is False
