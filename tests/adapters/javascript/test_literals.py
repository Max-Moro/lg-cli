"""
Tests for literal trimming in JavaScript adapter.
"""

from lg.adapters.javascript import JavaScriptCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_js, do_literals, assert_golden_match, make_adapter_real


class TestJavaScriptLiteralOptimizationGolden:
    """Test literal trimming for JavaScript code."""

    def test_basic_literal_trimming_budget_10(self, do_literals, lctx_js):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(JavaScriptCfg(literals=literal_config))

        result, meta = adapter.process(lctx_js(do_literals))

        assert meta.get("javascript.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals, lctx_js):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(JavaScriptCfg(literals=literal_config))

        result, meta = adapter.process(lctx_js(do_literals))

        assert meta.get("javascript.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")
