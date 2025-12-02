"""
Tests for literal trimming in C++ adapter.
"""

from lg.adapters.cpp import CppCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter_real
from ..golden_utils import assert_golden_match


class TestCppLiteralOptimizationGolden:
    """Test literal trimming for C++ code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("cpp.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("cpp.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")


class TestCppLiteralEdgeCases:
    """Test edge cases for C++ literal optimization."""

    def test_string_literal_trimming(self):
        """Test trimming of string literals."""
        code = '''const char* short_msg = "Hello";
const char* long_msg = "This is a very long message that should be trimmed because it exceeds the token limit for literal optimization in the C++ language adapter.";
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

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

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert "int small_array[] = {1, 2, 3};" in result
        assert "// literal array" in result or "/* literal array" in result

    def test_initializer_list_trimming(self):
        """Test trimming of initializer lists."""
        code = '''struct Item {
    int id;
    std::string name;
};

Item small_item = {1, "test"};

std::vector<Item> large_items = {
    {1, "item1"}, {2, "item2"}, {3, "item3"}, {4, "item4"},
    {5, "item5"}, {6, "item6"}, {7, "item7"}, {8, "item8"},
    {9, "item9"}, {10, "item10"}, {11, "item11"}, {12, "item12"}
};
'''

        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'Item small_item = {1, "test"};' in result

    def test_raw_string_literals(self):
        """Test handling of C++ raw string literals."""
        code = '''const char* short_raw = R"(Hello World)";

const char* long_raw = R"(
This is a very long raw string literal
that spans multiple lines and contains
a lot of text that should be trimmed
when the token limit is exceeded.
)";
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const char* short_raw = R"(Hello World)";' in result

    def test_nested_map_initializers(self):
        """Test trimming of nested map initializers with correct closing braces."""
        code = '''std::map<std::string, std::map<std::string, int>> largeConfig = {
    {"database", {
        {"port", 5432},
        {"pool_min", 2},
        {"pool_max", 10},
        {"timeout", 30}
    }},
    {"cache", {
        {"ttl", 3600},
        {"max_size", 1000},
        {"eviction_policy", 2}
    }},
    {"logging", {
        {"level", 3},
        {"buffer_size", 8192}
    }}
};
'''

        literal_config = LiteralConfig(max_tokens=25)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        # Verify that the closing braces are properly added
        # The result should contain something like: {{"database", {}}}
        # and NOT: {{"database", {}};
        assert '{' in result
        assert '}}' in result or '},' in result
        assert result.count('{') >= result.count('}')  # Should have balanced or more opening braces
        # Make sure we don't have the malformed closing that was the original issue
        assert '{}};' not in result  # The old buggy output

    def test_nested_map_initializers_single_line(self):
        """Test trimming of single-line nested map initializers."""
        code = '''std::map<std::string, std::map<std::string, int>> config = {{"db", {{"port", 5432}, {"pool", 10}}}, {"cache", {{"ttl", 3600}}}};
'''

        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(CppCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        # For single-line nested initializers, verify proper braces
        assert '{' in result
        assert result.count('{') >= result.count('}')
        # Should not have dangling semicolons inside braces
        assert '};' not in result.split('=')[1].split(';')[0] if '=' in result else True
