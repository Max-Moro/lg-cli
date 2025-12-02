"""
Tests for literal trimming in Rust adapter.
"""

from lg.adapters.rust import RustCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter_real
from ..golden_utils import assert_golden_match


class TestRustLiteralOptimizationGolden:
    """Test literal trimming for Rust code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic string literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("rust.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10", language="rust")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic string literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("rust.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20", language="rust")


class TestRustLiteralEdgeCases:
    """Test edge cases for Rust literal optimization."""

    def test_string_literal_trimming(self):
        """Test trimming of string literals."""
        code = '''const SHORT_MSG: &str = "Hello";
const LONG_MSG: &str = "This is a very long message that should be trimmed because it exceeds the token limit for literal optimization in the Rust language adapter.";
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const SHORT_MSG: &str = "Hello";' in result
        assert "// literal string" in result or "/* literal string" in result

    def test_vec_literal_trimming(self):
        """Test trimming of vec! literals."""
        code = '''let small_vec = vec![1, 2, 3];

let large_vec = vec![
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
];
'''

        literal_config = LiteralConfig(max_tokens=15)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert "let small_vec = vec![1, 2, 3];" in result
        assert "// literal array" in result or "/* literal array" in result

    def test_array_literal_trimming(self):
        """Test trimming of array literals."""
        code = '''const SMALL_ARRAY: [i32; 3] = [1, 2, 3];

const LARGE_ARRAY: [i32; 30] = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
];
'''

        literal_config = LiteralConfig(max_tokens=15)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert "const SMALL_ARRAY: [i32; 3] = [1, 2, 3];" in result

    def test_struct_literal_trimming(self):
        """Test trimming of struct literals."""
        code = '''struct Item {
    id: i32,
    name: String,
}

let small_item = Item { id: 1, name: "test".to_string() };

let large_items = vec![
    Item { id: 1, name: "item1".to_string() },
    Item { id: 2, name: "item2".to_string() },
    Item { id: 3, name: "item3".to_string() },
    Item { id: 4, name: "item4".to_string() },
    Item { id: 5, name: "item5".to_string() },
    Item { id: 6, name: "item6".to_string() },
    Item { id: 7, name: "item7".to_string() },
    Item { id: 8, name: "item8".to_string() },
    Item { id: 9, name: "item9".to_string() },
    Item { id: 10, name: "item10".to_string() },
];
'''

        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'let small_item = Item { id: 1, name: "test".to_string() };' in result

    def test_raw_string_literals(self):
        """Test handling of Rust raw string literals."""
        code = '''const SHORT_RAW: &str = r"Hello World";

const LONG_RAW: &str = r#"
This is a very long raw string literal
that spans multiple lines and contains
a lot of text that should be trimmed
when the token limit is exceeded.
"#;
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const SHORT_RAW: &str = r"Hello World";' in result

    def test_byte_string_literals(self):
        """Test handling of byte string literals."""
        code = '''const SMALL_BYTES: &[u8] = b"Hello";

const LARGE_BYTES: &[u8] = b"This is a very long byte string that should be trimmed when it exceeds the token limit for literal optimization.";
'''

        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(RustCfg(literals=literal_config))

        result, meta = adapter.process(lctx(code))

        assert 'const SMALL_BYTES: &[u8] = b"Hello";' in result
