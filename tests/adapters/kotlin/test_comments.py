"""
Tests for comment policy implementation in Kotlin adapter.
"""

from lg.adapters.kotlin import KotlinCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_kt, do_comments, assert_golden_match, make_adapter


class TestKotlinCommentOptimization:
    """Test comment processing for Kotlin code."""
    
    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(KotlinCfg(comment_policy="keep_all"))
        
        result, meta = adapter.process(lctx_kt(do_comments))
        
        # No comments should be removed
        assert meta.get("kotlin.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result
        
        assert_golden_match(result, "comments", "keep_all")
    
    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(KotlinCfg(comment_policy="strip_all"))
        
        result, meta = adapter.process(lctx_kt(do_comments))
        
        # Comments should be removed
        assert meta.get("kotlin.removed.comment", 0) > 0
        assert "// … comment omitted" in result
        
        assert_golden_match(result, "comments", "strip_all")
    
    def test_keep_doc_comments(self, do_comments):
        """Test keeping only KDoc documentation comments."""
        adapter = make_adapter(KotlinCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_kt(do_comments))
        
        # Regular comments should be removed, KDoc preserved
        assert meta.get("kotlin.removed.comment", 0) > 0
        assert "/**" in result
        # Regular comments should be replaced with placeholders
        assert "// Single-line comment at module level" not in result
        
        assert_golden_match(result, "comments", "keep_doc")
    
    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of KDoc comments."""
        adapter = make_adapter(KotlinCfg(comment_policy="keep_first_sentence"))
        
        result, meta = adapter.process(lctx_kt(do_comments))
        
        # KDoc should be truncated to first sentence
        assert meta.get("kotlin.removed.comment", 0) > 0
        
        assert_golden_match(result, "comments", "keep_first_sentence")
    
    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_tokens=30,
            keep_annotations=["TODO", "FIXME", "NOTE"],
            strip_patterns=["WARNING"]
        )
        
        adapter = make_adapter(KotlinCfg(comment_policy=comment_config))
        
        result, meta = adapter.process(lctx_kt(do_comments))
        
        # Should keep KDoc and annotation comments
        assert "TODO:" in result
        assert "FIXME:" in result
        # Should strip WARNING comments
        assert "WARNING:" not in result
        assert "// … comment omitted" in result
        
        assert_golden_match(result, "comments", "complex_policy")


class TestKotlinCommentEdgeCases:
    """Test edge cases for Kotlin comment optimization."""
    
    def test_inline_comments_with_types(self):
        """Test handling of inline comments with Kotlin types."""
        code = '''
data class Config(
    val timeout: Long,  // Connection timeout in milliseconds
    val retries: Int,   // Number of retry attempts
    val debug: Boolean  // Enable debug logging
)

val config = Config(
    timeout = 5000,    // 5 seconds
    retries = 3,       // Try 3 times
    debug = false      // Disable by default
)
'''
        
        adapter = make_adapter(KotlinCfg(comment_policy="strip_all"))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # Inline comments should be processed
        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("kotlin.removed.comment", 0) > 0
    
    def test_kdoc_detection(self):
        """Test proper KDoc comment detection."""
        code = '''
/**
 * This is a KDoc comment
 * @param data Input data
 */
fun processData(data: String) {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    println(data)
}
'''
        
        adapter = make_adapter(KotlinCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_kt(code))
        
        # KDoc should be preserved
        assert "/**" in result and "This is a KDoc comment" in result
        assert "@param data Input data" in result
        
        # Regular comments should be removed
        assert "/* This is a regular multi-line comment */" not in result
        assert "// This is a single-line comment" not in result

