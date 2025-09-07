"""
Tests for import optimization in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.python.imports import PythonImportClassifier, PythonImportAnalyzer
from lg.adapters.python.adapter import PythonDocument
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_py, do_imports, assert_golden_match


# TODO
