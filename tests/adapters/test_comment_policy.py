"""
Tests for comment policy implementation (M2).
"""

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript_tree_sitter import TypeScriptTreeSitterAdapter, TypeScriptCfg

pytestmark = pytest.mark.usefixtures("skip_if_no_tree_sitter")


class TestCommentPolicyPython:
    """Test comment policy for Python code."""
    
    def test_keep_all_policy(self):
        """Test that keep_all preserves all comments."""
        code = '''"""Module docstring."""
import os

# This is a comment
def hello():
    """Function docstring."""
    # Another comment
    return "hello"
'''
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_all")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should preserve all comments
        assert '"""Module docstring."""' in result
        assert '"""Function docstring."""' in result
        assert "# This is a comment" in result
        assert "# Another comment" in result
        assert meta["code.removed.comments"] == 0
    
    def test_strip_all_policy(self):
        """Test that strip_all removes all comments."""
        code = '''"""Module docstring."""
import os

# This is a comment  
def hello():
    """Function docstring."""
    # Another comment
    return "hello"
'''
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should remove all comments but add placeholders
        assert "# … comment omitted" in result or "# … docstring omitted" in result
        assert meta["code.removed.comments"] > 0
        
    def test_keep_doc_policy(self):
        """Test that keep_doc preserves docstrings but removes comments."""
        code = '''"""Module docstring."""
import os

# This is a comment
def hello():
    """Function docstring."""
    # Another comment
    return "hello"
'''
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_doc")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should preserve docstrings
        assert '"""Module docstring."""' in result
        assert '"""Function docstring."""' in result
        
        # Should remove regular comments
        assert "# … comment omitted" in result
        assert meta["code.removed.comments"] > 0
    
    def test_keep_first_sentence_policy(self):
        """Test that keep_first_sentence truncates docstrings."""
        code = '''"""This is the first sentence. This is the second sentence with more details."""
def hello():
    """Short description. Longer explanation that goes on."""
    return "hello"
'''
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_first_sentence")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should truncate to first sentence
        assert '"""This is the first sentence."""' in result
        assert '"""Short description."""' in result
        assert "second sentence" not in result
        assert "Longer explanation" not in result


class TestCommentPolicyTypeScript:
    """Test comment policy for TypeScript code."""
    
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
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="keep_all")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should preserve all comments
        assert "// This is a comment" in result
        assert "// inline comment" in result
        assert "JSDoc comment" in result
        assert "// Another comment" in result
        assert meta["code.removed.comments"] == 0
    
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
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should remove all comments but add placeholders
        assert "// … comment omitted" in result
        assert meta["code.removed.comments"] > 0


class TestCommentPolicyEdgeCases:
    """Test edge cases for comment policy."""
    
    def test_empty_file(self):
        """Test processing empty file."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process("", group_size=1, mixed=False)
        
        assert result == ""
        assert meta["code.removed.comments"] == 0
    
    def test_no_comments(self):
        """Test processing file without comments."""
        code = '''import os

def hello():
    return "hello"
'''
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        assert result == code  # Should be unchanged
        assert meta["code.removed.comments"] == 0
    
    def test_placeholder_styles(self):
        """Test different placeholder styles."""
        code = '''# This is a comment
def hello():
    return "hello"
'''
        
        # Test inline style (default)
        adapter = PythonTreeSitterAdapter() 
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        adapter._cfg.placeholders.style = "inline"
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        assert "# … comment omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(code, group_size=1, mixed=False)
        # For Python, block style might still use # comments
        assert "comment omitted" in result
