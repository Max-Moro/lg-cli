"""
Tests for comment policy implementation in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import CommentConfig
from .conftest import lctx_py, do_comments, assert_golden_match


class TestPythonCommentOptimization:
    """Test comment processing for Python code."""
    
    def test_keep_all_comments(self, do_comments):
        """Test keeping all comments (default policy)."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_all")
        
        result, meta = adapter.process(lctx_py(do_comments))
        
        # No comments should be removed
        assert meta.get("code.removed.comments", 0) == 0
        assert "# This is a regular comment" in result
        assert "# FIXME: Should use better data structure" in result
        assert '"""Module docstring with detailed description.' in result
        
        assert_golden_match(result, "comments", "keep_all")
    
    def test_strip_all_comments(self, do_comments):
        """Test stripping all comments."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(lctx_py(do_comments))
        
        # Comments should be removed
        assert meta.get("code.removed.comments", 0) > 0
        assert "# … comment omitted" in result or "… comment omitted" in result
        
        assert_golden_match(result, "comments", "strip_all")
    
    def test_keep_doc_comments(self, do_comments):
        """Test keeping only documentation comments."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_doc")
        
        result, meta = adapter.process(lctx_py(do_comments))
        
        # Regular comments should be removed, docstrings preserved
        assert meta.get("code.removed.comments", 0) > 0
        assert '"""Module docstring with detailed description.' in result
        assert '"""Class with various comment types."""' in result
        # Regular comments should be replaced with placeholders or removed
        assert "# This is a regular comment" not in result
        
        assert_golden_match(result, "comments", "keep_doc")
    
    def test_keep_first_sentence(self, do_comments):
        """Test keeping only first sentence of documentation."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_first_sentence")
        
        result, meta = adapter.process(lctx_py(do_comments))
        
        # Docstrings should be truncated to first sentence
        assert meta.get("code.removed.comments", 0) > 0
        assert "Module docstring with detailed description." in result
        # But not the full docstring
        assert "This module demonstrates various comment styles" not in result
        
        assert_golden_match(result, "comments", "keep_first_sentence")
    
    def test_complex_comment_policy(self, do_comments):
        """Test complex comment policy with custom configuration."""
        comment_config = CommentConfig(
            policy="keep_doc",
            max_length=100,
            keep_annotations=["TODO", "FIXME"],
            strip_patterns=["WARNING"]
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(do_comments))
        
        # Should keep docstrings and TODO/FIXME comments
        assert "TODO:" in result
        assert "FIXME:" in result
        # Should strip WARNING comments
        assert "WARNING:" not in result or "… comment omitted" in result
        
        assert_golden_match(result, "comments", "complex_policy")
    
    def test_comment_length_limiting(self):
        """Test comment length limiting."""
        code = '''def function():
    """This is a very long docstring that exceeds the maximum length limit and should be truncated to fit within the specified constraints for comment processing optimization."""
    pass
'''
        
        comment_config = CommentConfig(
            policy="keep_all",
            max_length=50
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Long docstring should be truncated
        assert "This is a very long docstring that exceed...""" in result
        assert "specified constraints" not in result
        
        assert_golden_match(result, "comments", "length_limiting")
    
    def test_annotation_preservation(self):
        """Test preservation of specific annotation patterns."""
        code = '''def process():
    # TODO: Implement better error handling
    # FIXME: This logic is flawed
    # NOTE: This is just informational
    # WARNING: Not implemented properly
    pass
'''
        
        comment_config = CommentConfig(
            policy="strip_all",
            keep_annotations=["TODO", "FIXME"]
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy=comment_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # TODO and FIXME should be preserved
        assert "TODO: Implement better error handling" in result
        assert "FIXME: This logic is flawed" in result
        # NOTE and WARNING should be stripped
        assert "NOTE: This is just informational" not in result
        assert "WARNING: Not implemented properly" not in result


class TestPythonCommentEdgeCases:
    """Test edge cases for Python comment optimization."""
    
    def test_inline_comments(self):
        """Test handling of inline comments."""
        code = '''value = 42  # This is an inline comment
another = "test"  # Another inline comment
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="strip_all")
        
        result, meta = adapter.process(lctx_py(code))
        
        # Inline comments should be processed
        assert "# This is an inline comment" not in result
        assert meta.get("code.removed.comments", 0) > 0
    
    def test_multiline_docstrings(self):
        """Test handling of multiline docstrings."""
        code = '''def complex_function():
    """
    This is a multiline docstring.
    
    It has multiple paragraphs and provides
    detailed information about the function.
    
    Args:
        None
        
    Returns:
        str: A processed string
    """
    return "result"
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_first_sentence")
        
        result, meta = adapter.process(lctx_py(code))
        
        # Should keep only first sentence
        assert "This is a multiline docstring." in result
        assert "It has multiple paragraphs" not in result
        assert "Args:" not in result
    
    def test_mixed_comment_types_in_class(self):
        """Test mixed comment types within a class."""
        code = '''class TestClass:
    """Class docstring."""
    
    def __init__(self):
        # Constructor comment
        self.value = 1  # Inline comment
    
    def method(self):
        """Method docstring."""
        # Method comment
        return self.value
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(comment_policy="keep_doc")
        
        result, meta = adapter.process(lctx_py(code))
        
        # Docstrings should be preserved
        assert '"""Class docstring."""' in result
        assert '"""Method docstring."""' in result
        # Regular comments should be removed
        assert "# Constructor comment" not in result
        assert "# Method comment" not in result
