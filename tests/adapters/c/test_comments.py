"""
Tests for comment policy implementation in C adapter.
"""

from lg.adapters.c import CCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCCommentOptimization:
    """Test comment processing for C code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(CCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("c.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This function performs comprehensive" in result

        assert_golden_match(result, "comments", "keep_all")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(CCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("c.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only documentation comments."""
        adapter = make_adapter(CCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("c.removed.comment", 0) > 0
        assert "/**" in result
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of documentation comments."""
        adapter = make_adapter(CCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("c.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(CCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy")


class TestCCommentEdgeCases:
    """Test edge cases for C comment optimization."""

    def test_inline_comments_with_declarations(self):
        """Test handling of inline comments with C declarations."""
        code = '''typedef struct {
    int timeout;     // Connection timeout in milliseconds
    int retries;     // Number of retry attempts
    int debug;       // Enable debug logging
} Config;

Config config = {
    5000,    // 5 seconds
    3,       // Try 3 times
    0        // Disable by default
};
'''

        adapter = make_adapter(CCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("c.removed.comment", 0) > 0

    def test_doc_comment_detection(self):
        """Test proper documentation comment detection."""
        code = '''/**
 * This is a documentation comment
 * @param data Input data
 */
void process_data(void* data) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    printf("Processing\\n");
}
'''

        adapter = make_adapter(CCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "This is a documentation comment" in result
        assert "@param data Input data" in result

        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

    def test_comment_preservation_in_structs(self):
        """Test comment preservation in C structs."""
        code = '''/**
 * User structure definition.
 */
typedef struct {
    /** User's unique identifier */
    int id;

    /** User's display name */
    char* name;

    // Internal field (not part of public API)
    void* metadata;
} User;
'''

        adapter = make_adapter(CCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "User structure definition" in result
        assert "/** User's unique identifier */" in result
        assert "/** User's display name */" in result

        assert "// Internal field" not in result

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''/*
 * Standard multiline comment
 * with multiple lines
 */
void standard_comment(void) {}

/**
 * Documentation style comment
 * with documentation
 */
void doc_comment(void) {}

/* Single line multiline comment */
void single_line_multi(void) {}
'''

        adapter = make_adapter(CCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "Documentation style comment" in result

        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result
