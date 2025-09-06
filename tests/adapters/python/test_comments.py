"""
Tests for comment policy implementation in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_py


class TestPythonCommentPolicyBasic:
    """Test basic comment policy for Python code."""
    
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
        
        result, meta = adapter.process(lctx_py(code))
        
        # Should preserve all comments
        assert '"""Module docstring."""' in result
        assert '"""Function docstring."""' in result
        assert "# This is a comment" in result
        assert "# Another comment" in result
        assert meta.get("code.removed.comments", 0) == 0
    
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
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(lctx_py(code))
        
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
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_doc")
        
        result, meta = adapter.process(lctx_py(code))
        
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
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_first_sentence")
        
        result, meta = adapter.process(lctx_py(code))
        
        # Should truncate to first sentence
        assert '"""This is the first sentence."""' in result
        assert '"""Short description."""' in result
        assert "second sentence" not in result
        assert "Longer explanation" not in result


class TestPythonCommentPolicyComplex:
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
        
        result, meta = adapter.process(lctx_py(code))
        
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
        
        result, meta = adapter.process(lctx_py(code))
        
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
        
        result, meta = adapter.process(lctx_py(code))
        
        # Should contain truncated comments with "..."
        assert "..." in result
        
        # No comment should be longer than max_length + "..."
        for line in result.split('\n'):
            if line.strip().startswith('#') or line.strip().startswith('"""'):
                # Allow some flexibility for quote characters and formatting
                assert len(line.strip()) <= 60  # 50 + some margin for quotes and ellipsis


class TestPythonCommentEdgeCases:
    """Test edge cases for Python comment policy."""
    
    def test_empty_file(self):
        """Test processing empty file."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")

        result, meta = adapter.process(lctx_py(""))

        assert result == ""
        assert meta.get("code.removed.comments", 0) == 0

    def test_no_comments(self):
        """Test processing file without comments."""
        code = '''import os

def hello():
    return "hello"
'''
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")

        result, meta = adapter.process(lctx_py(code))

        assert result == code  # Should be unchanged
        assert meta.get("code.removed.comments", 0) == 0
    
    def test_placeholder_styles(self):
        """Test different placeholder styles."""
        code = '''# This is a comment
def hello():
    return "hello"
'''
        
        # Test inline style (default)
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        adapter._cfg.placeholders.style = "inline"
        
        result, meta = adapter.process(lctx_py(code))
        assert "# … comment omitted" in result
        
        # Test block style
        adapter._cfg.placeholders.style = "block"
        result, meta = adapter.process(lctx_py(code))
        # For Python, block style might still use # comments
        assert "comment omitted" in result
