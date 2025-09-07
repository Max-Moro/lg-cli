"""
Tests for field optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FieldConfig
from .conftest import lctx_ts, do_fields, assert_golden_match


# TODO
