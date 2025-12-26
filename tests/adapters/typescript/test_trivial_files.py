"""
Tests for trivial file detection in TypeScript adapter.
"""

from pathlib import Path

from lg.adapters.langs.typescript import TypeScriptCfg
from .utils import lctx, make_adapter


def test_trivial(do_trivial):
    """Adapter should skip trivial index.ts via should_skip()."""
    adapter = make_adapter(TypeScriptCfg())

    ctx = lctx(do_trivial, Path("/src/components/index.ts"))
    assert adapter.should_skip(ctx) is True

def test_non_trivial(do_non_trivial):
    """Adapter should NOT skip non-trivial index.ts."""
    adapter = make_adapter(TypeScriptCfg())

    ctx = lctx(do_non_trivial, Path("/src/components/index.ts"))
    assert adapter.should_skip(ctx) is False

def test_adapter_should_not_skip_regular_file(do_trivial):
    """Adapter should NOT skip regular TypeScript files."""
    adapter = make_adapter(TypeScriptCfg())

    ctx = lctx(do_trivial, Path("/src/components/Button.ts"))
    assert adapter.should_skip(ctx) is False

def test_skip_trivial_files_config_disabled(do_trivial):
    """When skip_trivial_files=False, trivial files should NOT be skipped."""
    cfg = TypeScriptCfg()
    cfg.skip_trivial_files = False
    adapter = make_adapter(cfg)

    ctx = lctx(do_trivial, Path("/src/components/index.ts"))
    assert adapter.should_skip(ctx) is False
