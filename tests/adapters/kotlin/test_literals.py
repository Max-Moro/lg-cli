"""
Tests for literal trimming in Kotlin adapter.
"""

from lg.adapters.kotlin import KotlinCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestKotlinLiteralOptimizationGolden:
    """Test literal trimming for Kotlin code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(KotlinCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("kotlin.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(KotlinCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("kotlin.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")

