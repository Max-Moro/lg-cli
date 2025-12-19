"""
Tests for literal trimming in C adapter.
"""

from lg.adapters.c import CCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCLiteralOptimizationGolden:
    """Test literal trimming for C code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(CCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("c.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(CCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("c.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")


class TestCLiteralEdgeCases:
    """Test edge cases for C literal optimization."""

    def test_string_literal_trimming(self):
        """Test trimming of string literals."""
        code = '''const char* short_msg = "Hello";
const char* long_msg = "This is a very long message that should be trimmed because it exceeds the token limit for literal optimization in the C language adapter.";
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(CCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const char* short_msg = "Hello";' in result
        assert "// literal string" in result or "/* literal string" in result

    def test_array_literal_trimming(self):
        """Test trimming of array initializers."""
        code = '''int small_array[] = {1, 2, 3};

int large_array[] = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30
};
'''

        literal_config = LiteralConfig(max_tokens=15)

        adapter = make_adapter(CCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert "int small_array[] = {1, 2, 3};" in result
        assert "more" in result

    def test_struct_literal_trimming(self):
        """Test trimming of struct initializers."""
        code = '''typedef struct {
    int id;
    char* name;
} Item;

Item small_item = {1, "test"};

Item large_items[] = {
    {1, "item1"}, {2, "item2"}, {3, "item3"}, {4, "item4"},
    {5, "item5"}, {6, "item6"}, {7, "item7"}, {8, "item8"},
    {9, "item9"}, {10, "item10"}, {11, "item11"}, {12, "item12"}
};
'''

        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(CCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'Item small_item = {1, "test"};' in result
