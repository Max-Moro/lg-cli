"""
Tests for literal trimming in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_ts, do_literals, assert_golden_match, make_adapter_real


class TestTypeScriptLiteralOptimization:
    """Test literal trimming for TypeScript code."""

    def test_string_trimming_basic(self, do_literals):
        """Test basic string literal trimming."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(TypeScriptCfg(literals=literal_config))

        result, meta = adapter.process(lctx_ts(do_literals))

        assert_golden_match(result, "literals", "basic_trimming")
