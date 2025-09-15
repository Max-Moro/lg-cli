"""
Tests for comment policy implementation in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_ts, do_comments, assert_golden_match, make_adapter


class TestTypeScriptCommentOptimization:
    """Test comment processing for TypeScript code."""
    
    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_all"))
        
        result, meta = adapter.process(lctx_ts(do_comments))
        
        # No comments should be removed
        assert meta.get("typescript.removed.comment", 0) == 0
        assert "// Single-line comment at module level" in result
        assert "Multi-line comment explaining" in result
        assert "* This method performs comprehensive" in result
        
        assert_golden_match(result, "comments", "keep_all")
    
    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = make_adapter(TypeScriptCfg(comment_policy="strip_all"))
        
        result, meta = adapter.process(lctx_ts(do_comments))
        
        # Comments should be removed
        assert meta.get("typescript.removed.comment", 0) == 67
        assert "// … comment omitted" in result
        
        assert_golden_match(result, "comments", "strip_all")
    
    def test_keep_doc_comments(self, do_comments):
        """Test keeping only JSDoc documentation comments."""
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_ts(do_comments))
        
        # Regular comments should be removed, JSDoc preserved
        assert meta.get("typescript.removed.comment", 0) == 67
        assert "/**" in result and "Interface with JSDoc documentation" in result
        assert "* Class constructor with detailed JSDoc" in result
        # Regular comments should be replaced with placeholders
        assert "// Single-line comment at module level" not in result
        
        assert_golden_match(result, "comments", "keep_doc")
    
    def test_keep_first_sentence_policy(self, do_comments):
        """Test keeping only first sentence of JSDoc comments."""
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_first_sentence"))
        
        result, meta = adapter.process(lctx_ts(do_comments))
        
        # JSDoc should be truncated to first sentence
        assert meta.get("typescript.removed.comment", 0) == 67
        assert "Interface with JSDoc documentation." in result
        # But not the full documentation
        assert "This should be preserved when keeping documentation" not in result
        
        assert_golden_match(result, "comments", "keep_first_sentence")
    
    def test_jsdoc_detection(self):
        """Test proper JSDoc comment detection."""
        code = '''
/**
 * This is a JSDoc comment
 * @param data Input data
 */
function processData(data: string): void {
    /* This is a regular multi-line comment */
    // This is a single-line comment
    console.log(data);
}
'''
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # JSDoc should be preserved
        assert "/**" in result and "This is a JSDoc comment" in result
        assert "@param data Input data" in result
        
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
        
        adapter = make_adapter(TypeScriptCfg(comment_policy=comment_config))
        
        result, meta = adapter.process(lctx_ts(do_comments))
        
        # Should keep JSDoc and annotation comments
        assert "TODO:" in result
        assert "FIXME:" in result
        # Should strip WARNING comments
        assert "WARNING:" not in result
        assert "// … comment omitted" in result
        
        assert_golden_match(result, "comments", "complex_policy")


class TestTypeScriptCommentEdgeCases:
    """Test edge cases for TypeScript comment optimization."""
    
    def test_inline_comments_with_types(self):
        """Test handling of inline comments with TypeScript types."""
        code = '''
interface Config {
    timeout: number;  // Connection timeout in milliseconds
    retries: number;  // Number of retry attempts
    debug: boolean;   // Enable debug logging
}

const config: Config = {
    timeout: 5000,    // 5 seconds
    retries: 3,       // Try 3 times
    debug: false      // Disable by default
};
'''
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="strip_all"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Inline comments should be processed
        assert "// Connection timeout in milliseconds" not in result
        assert "// Number of retry attempts" not in result
        assert meta.get("typescript.removed.comment", 0) == 6
    
    def test_nested_jsdoc_tags(self):
        """Test handling of complex JSDoc with nested tags."""
        code = '''
/**
 * Complex function with detailed JSDoc.
 * 
 * @template T The type parameter
 * @param {T[]} items Array of items to process
 * @param {object} options Processing options
 * @param {boolean} options.validate Whether to validate items
 * @param {number} options.timeout Processing timeout
 * @returns {Promise<T[]>} Promise resolving to processed items
 * @throws {ValidationError} When validation fails
 * @example
 * ```typescript
 * const result = await processItems([1, 2, 3], { validate: true });
 * ```
 */
async function processItems<T>(
    items: T[], 
    options: { validate?: boolean; timeout?: number }
): Promise<T[]> {
    return items;
}
'''
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_first_sentence"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should keep only first sentence
        assert "Complex function with detailed JSDoc." in result
        # Should not keep detailed parameter documentation
        assert "@template T The type parameter" not in result
        assert "@param {T[]} items" not in result
    
    def test_comment_preservation_in_interfaces(self):
        """Test comment preservation in TypeScript interfaces."""
        code = '''
/**
 * User interface definition.
 */
interface User {
    /** User's unique identifier */
    id: number;
    
    /** User's display name */
    name: string;
    
    // Internal field (not part of public API)
    _metadata?: Record<string, any>;
}
'''
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Interface JSDoc should be preserved
        assert "/**" in result and "User interface definition" in result
        assert "/** User's unique identifier */" in result
        assert "/** User's display name */" in result
        
        # Regular comments should be removed
        assert "// Internal field" not in result
    
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
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Only JSDoc comments should be preserved
        assert "/**" in result and "JSDoc style comment" in result
        
        # Standard multiline comments should be removed
        assert "Standard multiline comment" not in result
        assert "Single line multiline comment" not in result
    
    def test_comment_in_generic_types(self):
        """Test comments in complex generic type definitions."""
        code = '''
/**
 * Generic utility type for API responses.
 */
type ApiResponse<T> = {
    data: T;           // The response payload
    success: boolean;  // Whether the request succeeded
    error?: string;    // Error message if any
};

// Type alias for user responses
type UserResponse = ApiResponse<User>;
'''
        
        adapter = make_adapter(TypeScriptCfg(comment_policy="keep_doc"))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # JSDoc should be preserved
        assert "/**" in result and "Generic utility type" in result
        
        # Inline and regular comments should be removed
        assert "// The response payload" not in result
        assert "// Type alias for user responses" not in result
