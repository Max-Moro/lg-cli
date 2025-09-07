"""
Complex integration tests for TypeScript adapter.
Tests combining multiple optimization types and edge cases.
"""

from lg.adapters.code_model import ImportConfig, LiteralConfig, FieldConfig
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from .conftest import lctx_ts, lctx, assert_golden_match, do_complex


# TODO
