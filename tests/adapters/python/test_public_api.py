"""
Tests for public API filtering in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_py, do_public_api, assert_golden_match


# TODO
