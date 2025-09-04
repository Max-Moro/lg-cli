"""
Tests for complex comment policy implementation (CommentConfig).
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_py, lctx_ts


class TestComplexCommentPolicyPython:
    """Test complex comment policy for Python code."""
    
    def test_keep_annotations_policy(self):
        """Test that keep_annotations preserves specified comments."""
        code = '''"""Module docstring."""
import os

# TODO: Implement this feature
def hello():
    """Function docstring."""
    # FIXME: This is broken
    # Regular comment that should be removed
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=[r"\bTODO\b", r"\bFIXME\b"]
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should preserve TODO and FIXME comments
        assert "# TODO: Implement this feature" in result
        assert "# FIXME: This is broken" in result
        
        # Should remove regular comment with placeholder
        assert "# … comment omitted" in result
        assert meta["code.removed.comments"] > 0
    
    def test_strip_patterns_policy(self):
        """Test that strip_patterns removes specified comments."""
        code = '''"""Module docstring."""
import os

# Copyright 2023 Company
# Licensed under MIT
# This is a useful comment
def hello():
    """Function docstring."""
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            strip_patterns=[r"\bCopyright\b", r"\bLicensed\b"]
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should remove copyright and license comments
        assert "# … comment omitted" in result
        assert meta["code.removed.comments"] > 0
        
        # Should preserve other comments
        assert "# This is a useful comment" in result
        assert '"""Module docstring."""' in result
        assert '"""Function docstring."""' in result
    
    def test_max_length_truncation(self):
        """Test that max_length truncates long comments."""
        code = '''"""This is a very long module docstring that should be truncated because it exceeds the maximum length limit."""
import os

# This is a very long single line comment that should also be truncated
def hello():
    """This is another long function docstring that will be cut off."""
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            max_length=50
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should contain truncated comments with "..."
        assert "..." in result
        
        # No comment should be longer than max_length + "..."
        for line in result.split('\n'):
            if line.strip().startswith('#') or line.strip().startswith('"""'):
                # Allow some flexibility for quote characters and formatting
                assert len(line.strip()) <= 60  # 50 + some margin for quotes and ellipsis
    
    def test_max_length_with_keep_annotations(self):
        """Test max_length applied to comments preserved by keep_annotations."""
        code = '''"""Module docstring."""
import os

# TODO: Implement this very long feature description that should be truncated
# Regular comment
def hello():
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=[r"\bTODO\b"],
            max_length=30
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should preserve TODO but truncate it
        assert "# TODO: Implement this very lo..." in result
        assert meta["code.removed.comments"] > 0  # Regular comment should be removed
    
    def test_priority_order_strip_patterns_over_keep_annotations(self):
        """Test that strip_patterns has priority over keep_annotations."""
        code = '''"""Module docstring."""
import os

# TODO: Remove this copyright notice
# FIXME: This should be kept
def hello():
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            keep_annotations=[r"\bTODO\b", r"\bFIXME\b"],
            strip_patterns=[r"\bcopyright\b"]
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # TODO with "copyright" should be stripped (strip_patterns wins)
        assert "# TODO: Remove this copyright notice" not in result
        assert "# … comment omitted" in result
        
        # FIXME without copyright should be kept
        assert "# FIXME: This should be kept" in result
    
    def test_keep_first_sentence_with_max_length(self):
        """Test keep_first_sentence policy combined with max_length."""
        code = '''"""This is the first sentence of a very long docstring. This is the second sentence that should be removed."""
def hello():
    """Short description is kept. But this longer explanation should be removed."""
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_first_sentence",
            max_length=30
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should extract first sentence and then apply max_length
        assert "This is the first..." in result or "This is the first sentence..." in result
        assert "second sentence" not in result
        assert "longer explanation" not in result


class TestComplexCommentPolicyTypeScript:
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
        # Should remove copyright header
        assert "/* … comment omitted */" in result or "// … comment omitted" in result
        assert meta["code.removed.comments"] > 0
        
        # Should preserve useful documentation
        assert "// This is useful documentation" in result


class TestComplexCommentPolicyEdgeCases:
    """Test edge cases for complex comment policy."""
    
    def test_empty_patterns(self):
        """Test behavior with empty pattern lists."""
        code = '''# TODO: Do something
# Regular comment
def hello():
    """Docstring."""
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_doc",
            keep_annotations=[],  # Empty list
            strip_patterns=[]     # Empty list
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should behave like normal keep_doc policy
        assert "# … comment omitted" in result  # Both TODO and regular comment removed
        assert '"""Docstring."""' in result  # Docstring preserved
    
    def test_zero_max_length(self):
        """Test behavior with zero max_length."""
        code = '''# Comment
def hello():
    """Docstring."""
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_all",
            max_length=0
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # All comments should be truncated to just "..." since max_length=0
        # Both comment and docstring should be affected
        assert "..." in result
        
        # Check that comments were actually processed (replaced with ...)
        lines = result.strip().split('\n')
        ellipsis_lines = [line for line in lines if line.strip() == "..."]
        assert len(ellipsis_lines) >= 1  # At least one comment/docstring should become "..."
    
    def test_regex_case_sensitivity(self):
        """Test that regex patterns are case-insensitive."""
        code = '''# todo: lowercase
# TODO: uppercase 
# ToDo: mixed case
def hello():
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=[r"\btodo\b"]  # lowercase pattern
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # All variations should be preserved due to case-insensitive matching
        assert "# todo: lowercase" in result
        assert "# TODO: uppercase" in result
        assert "# ToDo: mixed case" in result
    
    def test_malformed_regex_patterns(self):
        """Test behavior with malformed regex patterns."""
        code = '''# TODO: Do something
def hello():
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=["[invalid_regex"]  # Malformed regex
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        # Should handle regex errors gracefully
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should fall back to base policy (strip_all)
        assert "# … comment omitted" in result
    
    def test_complex_policy_inheritance(self):
        """Test complex policy combined with base policy inheritance."""
        code = '''"""Module docstring."""
# TODO: Important note
# Regular comment
def hello():
    """Function docstring.""" 
    # Another regular comment
    return "hello"
'''
        adapter = PythonAdapter()
        comment_config = CommentConfig(
            policy="keep_doc",  # Base policy
            keep_annotations=[r"\bTODO\b"],
            max_length=100
        )
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should preserve docstrings (base policy)
        assert '"""Module docstring."""' in result
        assert '"""Function docstring."""' in result
        
        # Should preserve TODO (keep_annotations override)
        assert "# TODO: Important note" in result
        
        # Should remove regular comments (base policy)
        assert "# … comment omitted" in result
        assert meta["code.removed.comments"] > 0
