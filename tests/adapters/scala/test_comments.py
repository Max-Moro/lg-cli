"""
Tests for comment policy implementation in Scala adapter.
"""

from lg.adapters.langs.scala import ScalaCfg
from lg.adapters.code_model import CommentConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestScalaCommentOptimization:
    """Test comment processing for Scala code."""

    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(ScalaCfg(comment_policy="keep_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("scala.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result

        assert_golden_match(result, "comments", "keep_all")

    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(ScalaCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("scala.removed.comment", 0) > 0
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "strip_all")

    def test_keep_doc_comments(self, do_comments):
        """Test keeping only Scaladoc documentation comments."""
        adapter = make_adapter(ScalaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("scala.removed.comment", 0) > 0
        assert "/**" in result
        assert "// Single-line comment at module level" not in result

        assert_golden_match(result, "comments", "keep_doc")

    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of Scaladoc comments."""
        adapter = make_adapter(ScalaCfg(comment_policy="keep_first_sentence"))

        result, meta = adapter.process(lctx(do_comments))

        assert meta.get("scala.removed.comment", 0) > 0

        assert_golden_match(result, "comments", "keep_first_sentence")

    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )

        adapter = make_adapter(ScalaCfg(comment_policy=comment_config))

        result, meta = adapter.process(lctx(do_comments))

        assert "TODO:" in result
        assert "FIXME:" in result
        assert "WARNING:" not in result
        assert "// … comment omitted" in result

        assert_golden_match(result, "comments", "complex_policy")


class TestScalaCommentEdgeCases:
    """Test edge cases for Scala comment optimization."""

    def test_inline_comments_with_types(self):
        """Test handling of inline comments with Scala types."""
        code = '''
case class Config(
  timeout: Long,  // Connection timeout in milliseconds
  retries: Int,   // Number of retry attempts
  debug: Boolean  // Enable debug logging
)

val config = Config(
  timeout = 5000,    // 5 seconds
  retries = 3,       // Try 3 times
  debug = false      // Disable by default
)
'''

        adapter = make_adapter(ScalaCfg(comment_policy="strip_all"))

        result, meta = adapter.process(lctx(code))

        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("scala.removed.comment", 0) > 0

    def test_scaladoc_detection(self):
        """Test proper Scaladoc comment detection."""
        code = '''
/**
 * This is a Scaladoc comment
 * @param data Input data
 */
def processData(data: String): Unit = {
  /* This is a regular multi-line comment */
  // This is a single-line comment
  println(data)
}
'''

        adapter = make_adapter(ScalaCfg(comment_policy="keep_doc"))

        result, meta = adapter.process(lctx(code))

        assert "/**" in result and "This is a Scaladoc comment" in result
        assert "@param data Input data" in result

        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result
