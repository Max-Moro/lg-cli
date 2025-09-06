"""
Tests for comment policy implementation in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import CommentConfig
from .conftest import create_typescript_context


class TestTypeScriptCommentPolicyBasic:
    """Test basic comment policy for TypeScript code."""
    
    def test_keep_all_policy(self):
        """Test that keep_all preserves all comments."""
        code = '''// This is a comment
interface User {
    name: string; // inline comment
}

/**
 * JSDoc comment
 */
function greet(user: User) {
    // Another comment
    return `Hello, ${user.name}`;
}
'''
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="keep_all")
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should preserve all comments
        assert "// This is a comment" in result
        assert "// inline comment" in result
        assert "JSDoc comment" in result
        assert "// Another comment" in result
        assert meta.get("code.removed.comments", 0) == 0
    
    def test_strip_all_policy(self):
        """Test that strip_all removes all comments."""
        code = '''// This is a comment
interface User {
    name: string; // inline comment
}

/**
 * JSDoc comment
 */
function greet(user: User) {
    // Another comment
    return `Hello, ${user.name}`;
}
'''
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should remove all comments but add placeholders
        assert "// … comment omitted" in result
        assert meta["code.removed.comments"] > 0


class TestTypeScriptCommentPolicyComplex:
    """Test complex comment policy for TypeScript code."""
    
    def test_keep_annotations_policy(self):
        """Test that keep_annotations preserves specified comments in TypeScript."""
        code = '''// TODO: Implement this interface
interface User {
    name: string; // This should be removed
}

/**
 * FIXME: Update this method
 * @param user User object
 */
function greet(user: User) {
    // Another comment to remove
    return `Hello, ${user.name}`;
}
'''
        adapter = TypeScriptAdapter()
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=[r"\bTODO\b", r"\bFIXME\b"]
        )
        adapter._cfg = TypeScriptCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should preserve TODO and FIXME comments
        assert "// TODO: Implement this interface" in result
        assert "FIXME: Update this method" in result
        
        # Should remove other comments
        assert "// … comment omitted" in result or "/* … comment omitted */" in result
        assert meta["code.removed.comments"] > 0
    
    def test_max_length_with_jsdoc(self):
        """Test max_length applied to JSDoc comments."""
        code = '''/**
 * This is a very long JSDoc comment that describes the function in great detail and should be truncated.
 * @param user The user object with all properties
 * @returns A greeting string
 */
function greet(user: User) {
    return `Hello, ${user.name}`;
}
'''
        adapter = TypeScriptAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            max_length=60
        )
        adapter._cfg = TypeScriptCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should contain truncated comment
        assert "..." in result
    
    def test_strip_patterns_copyright(self):
        """Test stripping copyright headers in TypeScript."""
        code = '''/**
 * Copyright (c) 2023 Company Name
 * All rights reserved.
 */

// This is useful documentation
interface User {
    name: string;
}
'''
        adapter = TypeScriptAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            strip_patterns=[r"\bCopyright\b", r"All rights reserved"]
        )
        adapter._cfg = TypeScriptCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should remove copyright header
        assert "/* … comment omitted */" in result or "// … comment omitted" in result
        assert meta["code.removed.comments"] > 0
        
        # Should preserve useful documentation
        assert "// This is useful documentation" in result


class TestTypeScriptCommentEdgeCases:
    """Test edge cases for TypeScript comment policy."""
    
    def test_empty_file(self):
        """Test processing empty TypeScript file."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="strip_all")

        result, meta = adapter.process(create_typescript_context(""))

        assert result == ""
        assert meta.get("code.removed.comments", 0) == 0

    def test_no_comments(self):
        """Test processing TypeScript file without comments."""
        code = '''interface User {
    name: string;
}

function greet(user: User) {
    return `Hello, ${user.name}`;
}
'''
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="strip_all")

        result, meta = adapter.process(create_typescript_context(code))

        assert result == code  # Should be unchanged
        assert meta.get("code.removed.comments", 0) == 0
    
    def test_placeholder_styles(self):
        """Test different placeholder styles for TypeScript."""
        code = '''// This is a comment
function test() {
    return 42;
}
'''
        
        # Test inline style (default)
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="strip_all")
        adapter._cfg.placeholders.style = "inline"
        
        result, meta = adapter.process(create_typescript_context(code))
        assert "// … comment omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(create_typescript_context(code))
        # For TypeScript, block style uses /* */ comments
        assert "comment omitted" in result
