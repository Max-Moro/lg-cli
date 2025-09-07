"""
Tests for literal trimming in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_ts, do_literals, assert_golden_match


# TODO
