"""
Tests for comment policy implementation in Rust adapter.
"""

from lg.adapters.langs.rust import RustCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestRustCommentOptimization:
    """Test comment processing for Rust code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(RustCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("rust.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "/// User represents" in result

        assert_golden_match(result, "comments", "keep_all", language="rust")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(RustCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("rust.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all", language="rust")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only documentation comments."""
        adapter = make_adapter(RustCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("rust.removed.comment", 0) > 0
        assert "///" in result
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc", language="rust")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of documentation comments."""
        adapter = make_adapter(RustCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("rust.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence", language="rust")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(RustCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy", language="rust")


class TestRustCommentEdgeCases:
    """Test edge cases for Rust comment optimization."""

    def test_inline_comments_with_declarations(self):
        """Test handling of inline comments with Rust declarations."""
        code = '''struct Config {
    timeout: i32,       // Connection timeout in milliseconds
    retries: i32,       // Number of retry attempts
    debug: bool,        // Enable debug logging
}

let config = Config {
    timeout: 5000,    // 5 seconds
    retries: 3,       // Try 3 times
    debug: false,     // Disable by default
};
'''

        adapter = make_adapter(RustCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("rust.removed.comment", 0) > 0

    def test_doc_comment_detection(self):
        """Test proper documentation comment detection."""
        code = '''/// This is a documentation comment
/// for the function below.
fn process_data(data: &str) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    println!("{}", data);
}
'''

        adapter = make_adapter(RustCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/// This is a documentation comment" in result
        assert "/// for the function below." in result

        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

    def test_comment_preservation_in_structs(self):
        """Test comment preservation in Rust structs."""
        code = '''/// User struct definition.
pub struct User {
    /// User's unique identifier
    id: i32,

    /// User's display name
    name: String,

    // Internal field (not part of public API)
    metadata: Option<String>,
}
'''

        adapter = make_adapter(RustCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/// User struct definition." in result
        assert "/// User's unique identifier" in result
        assert "/// User's display name" in result

        assert "// Internal field" not in result

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''/*
 * Standard multiline comment
 * with multiple lines
 */
fn standard_comment() {}

/**
 * Documentation style comment
 * with documentation
 */
fn doc_comment() {}

/* Single line multiline comment */
fn single_line_multi() {}
'''

        adapter = make_adapter(RustCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "Documentation style comment" in result

        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result

    def test_inner_doc_comments(self):
        """Test inner documentation comments (//! and /*!)."""
        code = '''//! This is a module-level inner doc comment.
//! It describes the module.

/*! Another form of inner doc comment
 * spanning multiple lines.
 */

/// Outer doc comment for function
fn my_function() {
    // Regular comment
    println!("Hello");
}
'''

        adapter = make_adapter(RustCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "//! This is a module-level inner doc comment." in result
        assert "/*!" in result

        assert "// Regular comment" not in result
