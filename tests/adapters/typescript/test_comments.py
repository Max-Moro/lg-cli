"""
Tests for comment policy implementation in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_ts, do_comments, assert_golden_match


# TODO
