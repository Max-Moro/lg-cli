"""
Tests for public API filtering in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_ts, do_public_api, assert_golden_match


# TODO
