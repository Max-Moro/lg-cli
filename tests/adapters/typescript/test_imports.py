"""
Tests for import optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.typescript.imports import TypeScriptImportClassifier, TypeScriptImportAnalyzer
from lg.adapters.typescript.adapter import TypeScriptDocument
from lg.adapters.code_model import ImportConfig
from .conftest import lctx_ts, do_imports, assert_golden_match


# TODO
