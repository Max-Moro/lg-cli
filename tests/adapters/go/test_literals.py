"""
Tests for literal trimming in Go adapter.
"""

from lg.adapters.go import GoCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter_real
from ..golden_utils import assert_golden_match


class TestGoLiteralOptimizationGolden:
    """Test literal trimming for Go code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("go.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10", language="go")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("go.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20", language="go")


class TestGoLiteralEdgeCases:
    """Test edge cases for Go literal optimization."""

    def test_string_literal_trimming(self):
        """Test trimming of string literals."""
        code = '''package main

const shortMsg = "Hello"
const longMsg = "This is a very long message that should be trimmed because it exceeds the token limit for literal optimization in the Go language adapter."
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const shortMsg = "Hello"' in result
        assert "// … literal string" in result or "/* literal string" in result

    def test_slice_literal_trimming(self):
        """Test trimming of slice literals."""
        code = '''package main

var smallSlice = []int{1, 2, 3}

var largeSlice = []int{
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
}
'''

        literal_config = LiteralConfig(max_tokens=15)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert "var smallSlice = []int{1, 2, 3}" in result
        assert "// … literal array" in result or "/* literal array" in result

    def test_struct_literal_trimming(self):
        """Test trimming of struct literals."""
        code = '''package main

type Item struct {
    ID   int
    Name string
}

var smallItem = Item{ID: 1, Name: "test"}

var largeItems = []Item{
    {ID: 1, Name: "item1"}, {ID: 2, Name: "item2"}, {ID: 3, Name: "item3"},
    {ID: 4, Name: "item4"}, {ID: 5, Name: "item5"}, {ID: 6, Name: "item6"},
    {ID: 7, Name: "item7"}, {ID: 8, Name: "item8"}, {ID: 9, Name: "item9"},
    {ID: 10, Name: "item10"}, {ID: 11, Name: "item11"}, {ID: 12, Name: "item12"},
}
'''

        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'var smallItem = Item{ID: 1, Name: "test"}' in result

    def test_map_literal_trimming(self):
        """Test trimming of map literals."""
        code = '''package main

var smallConfig = map[string]interface{}{
    "debug": true,
    "version": "1.0.0",
}

var largeConfig = map[string]interface{}{
    "database": map[string]interface{}{
        "host": "localhost",
        "port": 5432,
        "name": "app_db",
        "ssl":  false,
        "pool": map[string]int{
            "min": 2,
            "max": 10,
            "idleTimeout": 30000,
            "connectionTimeout": 2000,
        },
    },
    "cache": map[string]interface{}{
        "redis": map[string]interface{}{
            "host": "localhost",
            "port": 6379,
            "db":   0,
            "ttl":  3600,
        },
    },
}
'''

        literal_config = LiteralConfig(max_tokens=30)

        adapter = make_adapter_real(GoCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'var smallConfig = map[string]interface{}{' in result
