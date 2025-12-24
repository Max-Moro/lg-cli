"""
Tests for comment policy implementation in C++ adapter.
"""

from lg.adapters.langs.cpp import CppCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCppCommentOptimization:
    """Test comment processing for C++ code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(CppCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("cpp.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result

        assert_golden_match(result, "comments", "keep_all")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(CppCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("cpp.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only documentation comments."""
        adapter = make_adapter(CppCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("cpp.removed.comment", 0) > 0
        assert "/**" in result
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of documentation comments."""
        adapter = make_adapter(CppCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("cpp.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(CppCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy")


class TestCppCommentEdgeCases:
    """Test edge cases for C++ comment optimization."""

    def test_inline_comments_with_declarations(self):
        """Test handling of inline comments with C++ declarations."""
        code = '''struct Config {
    int timeout;       // Connection timeout in milliseconds
    int retries;       // Number of retry attempts
    bool debug;        // Enable debug logging
};

Config config = {
    5000,    // 5 seconds
    3,       // Try 3 times
    false    // Disable by default
};
'''

        adapter = make_adapter(CppCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("cpp.removed.comment", 0) > 0

    def test_doxygen_comment_detection(self):
        """Test proper Doxygen comment detection."""
        code = '''/**
 * This is a Doxygen comment
 * @param data Input data
 */
void processData(void* data) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    printf("Processing\\n");
}
'''

        adapter = make_adapter(CppCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "This is a Doxygen comment" in result
        assert "@param data Input data" in result

        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

    def test_comment_preservation_in_classes(self):
        """Test comment preservation in C++ classes."""
        code = '''/**
 * User class definition.
 */
class User {
    /** User's unique identifier */
    int id;

    /** User's display name */
    std::string name;

    // Internal field (not part of public API)
    void* metadata;
};
'''

        adapter = make_adapter(CppCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "User class definition" in result
        assert "/** User's unique identifier */" in result
        assert "/** User's display name */" in result

        assert "// Internal field" not in result

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''/*
 * Standard multiline comment
 * with multiple lines
 */
void standardComment() {}

/**
 * Documentation style comment
 * with documentation
 */
void docComment() {}

/* Single line multiline comment */
void singleLineMulti() {}
'''

        adapter = make_adapter(CppCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "Documentation style comment" in result

        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result

    def test_triple_slash_doxygen_comments(self):
        """Test triple-slash Doxygen comment style."""
        code = '''/// This is a triple-slash Doxygen comment
/// @param x The input value
/// @return The result
int compute(int x) {
    // Regular comment
    return x * 2;
}
'''

        adapter = make_adapter(CppCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/// This is a triple-slash Doxygen comment" in result
        assert "/// @param x The input value" in result

        assert "// Regular comment" not in result
