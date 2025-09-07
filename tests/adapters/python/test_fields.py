"""
Tests for field optimization in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FieldConfig, LiteralConfig
from .conftest import lctx_py, do_fields, assert_golden_match


# TODO
