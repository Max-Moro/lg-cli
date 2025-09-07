"""
Tests for literal trimming in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_py, do_literals, assert_golden_match


# TODO
