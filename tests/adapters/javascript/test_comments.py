"""
Tests for comment policy implementation in JavaScript adapter.
"""

from lg.adapters.javascript import JavaScriptCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestJavaScriptCommentOptimization:
    """Test comment processing for JavaScript code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        # No comments should be removed
        assert meta.get("javascript.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result

        assert_golden_match(result, "comments", "keep_all")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(JavaScriptCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        # Comments should be removed
        assert meta.get("javascript.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only JSDoc documentation comments."""
        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        # Regular comments should be removed, JSDoc preserved
        assert meta.get("javascript.removed.comment", 0) > 0
        assert "/**" in result and "User class with JSDoc documentation" in result
        assert "* Class constructor with detailed JSDoc" in result
        # Regular comments should be replaced with placeholders
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of JSDoc comments."""
        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        # JSDoc should be truncated to first sentence
        assert meta.get("javascript.removed.comment", 0) > 0
        assert "User class with JSDoc documentation." in result
        # But not the full documentation
        assert "This should be preserved when keeping documentation" not in result

        assert_golden_match(result, "comments", "keep_first_sentence")

    def test_jsdoc_detection(self):
        """Test proper JSDoc comment detection."""
        code = '''
/**
 * This is a JSDoc comment
 * @param {string} data Input data
 */
function processData(data) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    console.log(data);
}
'''

        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        # JSDoc should be preserved
        assert "/**" in result and "This is a JSDoc comment" in result
        assert "@param {string} data Input data" in result

        # Regular comments should be removed
        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING", "DEPRECATED"]
        )

        adapter = make_adapter(JavaScriptCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        # Should keep JSDoc and annotation comments
        assert "TODO:" in result
        assert "FIXME:" in result
        # Should strip WARNING comments
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy")


class TestJavaScriptCommentEdgeCases:
    """Test edge cases for JavaScript comment optimization."""

    def test_inline_comments_with_code(self):
        """Test handling of inline comments."""
        code = '''
const config = {
    timeout: 5000,    // Connection timeout in milliseconds
    retries: 3,       // Number of retry attempts
    debug: false      // Enable debug logging
};
'''

        adapter = make_adapter(JavaScriptCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        # Inline comments should be processed
        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("javascript.removed.comment", 0) > 0

    def test_nested_jsdoc_tags(self):
        """Test handling of complex JSDoc with nested tags."""
        code = '''
/**
 * Complex function with detailed JSDoc.
 *
 * @template T The type parameter
 * @param {T[]} items Array of items to process
 * @param {Object} options Processing options
 * @param {boolean} options.validate Whether to validate items
 * @param {number} options.timeout Processing timeout
 * @returns {Promise<T[]>} Promise resolving to processed items
 * @throws {ValidationError} When validation fails
 * @example
 * const result = await processItems([1, 2, 3], { validate: true });
 */
async function processItems(items, options) {
    return items;
}
'''

        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(code))

        # Should keep only first sentence
        assert "Complex function with detailed JSDoc." in result
        # Should not keep detailed parameter documentation
        assert "@template T The type parameter" not in result
        assert "@param {T[]} items" not in result

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''
/*
 * Standard multiline comment
 * with multiple lines
 */
function standardComment() {}

/**
 * JSDoc style comment
 * with documentation
 */
function jsdocComment() {}

/* Single line multiline comment */
function singleLineMulti() {}
'''

        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        # Only JSDoc comments should be preserved
        assert "/**" in result and "JSDoc style comment" in result

        # Standard multiline comments should be removed
        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result

    def test_comment_in_object_literals(self):
        """Test comments in object literals."""
        code = '''
const config = {
    // Database settings
    database: {
        host: 'localhost',
        port: 5432
    },
    // Cache settings
    cache: {
        enabled: true,
        ttl: 3600
    }
};
'''

        adapter = make_adapter(JavaScriptCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        # Regular comments should be removed
        assert "// Database settings" not in result
        assert "// Cache settings" not in result
