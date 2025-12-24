"""
Tests for comment policy implementation in Go adapter.
"""

from lg.adapters.langs.go import GoCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestGoCommentOptimization:
    """Test comment processing for Go code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(GoCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("go.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result

        assert_golden_match(result, "comments", "keep_all", language="go")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(GoCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("go.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all", language="go")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only documentation comments."""
        adapter = make_adapter(GoCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("go.removed.comment", 0) > 0
        # Doc comments before exported declarations should be preserved
        assert "// Single-line comment at module level" in result
        assert "// User represents a user with documentation comments." in result

        assert_golden_match(result, "comments", "keep_doc", language="go")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of documentation comments."""
        adapter = make_adapter(GoCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("go.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence", language="go")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(GoCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy", language="go")


class TestGoCommentEdgeCases:
    """Test edge cases for Go comment optimization."""

    def test_inline_comments_with_declarations(self):
        """Test handling of inline comments with Go declarations."""
        code = '''package main

type Config struct {
    Timeout int    // Connection timeout in milliseconds
    Retries int    // Number of retry attempts
    Debug   bool   // Enable debug logging
}

var config = Config{
    Timeout: 5000,    // 5 seconds
    Retries: 3,       // Try 3 times
    Debug:   false,   // Disable by default
}
'''

        adapter = make_adapter(GoCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("go.removed.comment", 0) > 0

    def test_doc_comment_detection(self):
        """Test Go comment handling with keep_doc policy.

        With GoCommentAnalyzer, we can now distinguish doc comments from regular comments
        using positional analysis. Doc comments before exported declarations are preserved.
        """
        code = '''package main

// ProcessData processes the input data.
// This is a documentation comment.
func ProcessData(data string) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    println(data)
}
'''

        adapter = make_adapter(GoCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        # Doc comment before exported function should be preserved
        assert "ProcessData processes the input data." in result
        assert "This is a documentation comment." in result
        # Regular comments inside function should be removed
        assert "This is a regular multi-line comment" not in result
        assert "This is a single-line comment" not in result
        assert meta.get("go.removed.comment", 0) > 0

    def test_multiline_comment_styles(self):
        """Test different multiline comment styles."""
        code = '''package main

/*
 * Standard multiline comment
 * with multiple lines
 */
func standardComment() {}

/*
 * Documentation style comment
 * with documentation
 */
func docComment() {}

/* Single line multiline comment */
func singleLineMulti() {}
'''

        adapter = make_adapter(GoCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result
