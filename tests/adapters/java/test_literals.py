"""
Tests for literal trimming in Java adapter.
"""

from lg.adapters.code_model import LiteralConfig
from lg.adapters.java import JavaCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaLiteralOptimizationGolden:
    """Test literal trimming for Java code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(JavaCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("java.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(JavaCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("java.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")



class TestJavaLegacyDoubleBraceInitialization:
    """
    Test literal trimming for Java legacy double-brace initialization pattern.
    """

    def test_legacy_double_brace_budget_10(self, do_literals_legacy):
        """Test double-brace initialization trimming with 10 tokens budget.
        """
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(JavaCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals_legacy))

        # Count imperative method calls before and after
        original_puts = do_literals_legacy.count('put(')
        optimized_puts = result.count('put(')
        original_adds = do_literals_legacy.count('add(')
        optimized_adds = result.count('add(')

        # Should have removed imperative initialization statements (put/add calls)
        statements_removed = (original_puts - optimized_puts) + (original_adds - optimized_adds)
        assert statements_removed > 0, \
            f"BLOCK_INIT not yet implemented - should remove some put()/add() calls. " \
            f"Original: {original_puts} put + {original_adds} add, " \
            f"Optimized: {optimized_puts} put + {optimized_adds} add"

        assert_golden_match(result, "literals", "legacy_max_tokens_10")

    def test_legacy_double_brace_budget_20(self, do_literals_legacy):
        """Test double-brace initialization trimming with 20 tokens budget.
        """
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(JavaCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals_legacy))

        # Count imperative method calls before and after
        original_puts = do_literals_legacy.count('put(')
        optimized_puts = result.count('put(')
        original_adds = do_literals_legacy.count('add(')
        optimized_adds = result.count('add(')

        # Should have removed some imperative initialization statements
        statements_removed = (original_puts - optimized_puts) + (original_adds - optimized_adds)
        assert statements_removed > 0, \
            f"BLOCK_INIT not yet implemented - should remove some put()/add() calls. " \
            f"Original: {original_puts} put + {original_adds} add, " \
            f"Optimized: {optimized_puts} put + {optimized_adds} add"

        assert_golden_match(result, "literals", "legacy_max_tokens_20")
