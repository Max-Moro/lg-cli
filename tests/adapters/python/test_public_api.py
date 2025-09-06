"""
Tests for public API filtering in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_py


class TestPythonPublicAPIFiltering:
    """Test public API filtering for Python code."""
    
    def test_public_api_only_filters_private_methods(self):
        """Test that public_api_only removes private methods."""
        code = '''class Calculator:
    """A simple calculator class."""
    
    def add(self, a, b):
        """Public method."""
        return a + b
    
    def _helper(self, x):
        """Private helper method."""
        return x * 2
    
    def __internal(self):
        """Private method with double underscore."""
        pass
    
    def __init__(self):
        """Special method should be kept."""
        pass
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public methods should be preserved
        assert "def add(self, a, b):" in result
        assert "def __init__(self):" in result  # Special methods are public
        
        # Private methods should be removed
        assert "def _helper(self, x):" not in result
        assert "def __internal(self):" not in result
        
        # Should have placeholders for removed elements
        assert "… private element omitted" in result
        assert meta.get("code.removed.private_elements", 0) > 0
    
    def test_public_api_only_filters_private_functions(self):
        """Test that public_api_only removes private functions."""
        code = '''def public_function():
    """This is public."""
    return "public"

def _private_function():
    """This is private.""" 
    return "private"

def __very_private():
    """This is very private."""
    return "very private"
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public function should be preserved
        assert "def public_function():" in result
        
        # Private functions should be removed
        assert "def _private_function():" not in result
        assert "def __very_private():" not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
    
    def test_public_only_function_body_stripping(self):
        """Test public_only mode for function body stripping."""
        code = '''def public_function():
    """Public function with body."""
    x = 1
    y = 2
    return x + y

def _private_function():
    """Private function with body."""
    a = 10
    b = 20
    return a * b
'''
        
        adapter = PythonAdapter()
        function_config = FunctionBodyConfig(mode="public_only")
        adapter._cfg = PythonCfg(strip_function_bodies=function_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public function body should be stripped
        assert "def public_function():" in result
        assert "# … body omitted" in result or "# … function omitted" in result
        assert "x = 1" not in result
        
        # Private function body should be preserved (it's not public)
        assert "def _private_function():" in result
        assert "a = 10" in result
        
        assert meta.get("code.removed.functions", 0) > 0
    
    def test_non_public_function_body_stripping(self):
        """Test non_public mode for function body stripping."""
        code = '''def public_function():
    """Public function with body."""
    x = 1
    y = 2
    return x + y

def _private_function():
    """Private function with body."""
    a = 10
    b = 20
    return a * b
'''
        
        adapter = PythonAdapter()
        function_config = FunctionBodyConfig(mode="non_public")
        adapter._cfg = PythonCfg(strip_function_bodies=function_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public function body should be preserved
        assert "def public_function():" in result
        assert "x = 1" in result
        
        # Private function body should be stripped
        assert "def _private_function():" in result
        assert "# … body omitted" in result or "# … function omitted" in result
        assert "a = 10" not in result
        
        assert meta.get("code.removed.functions", 0) > 0


class TestPythonPublicAPIEdgeCases:
    """Test edge cases for Python public API filtering."""
    
    def test_empty_class(self):
        """Test handling of empty classes."""
        code = '''class EmptyClass:
    pass
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Empty public class should be preserved
        assert "class EmptyClass:" in result
    
    def test_mixed_visibility_class(self):
        """Test class with mixed public/private methods."""
        code = '''class MixedClass:
    def public_method(self):
        return "public"
    
    def _private_method(self):
        return "private"
    
    @property
    def public_property(self):
        return self._value
    
    @property  
    def _private_property(self):
        return self._internal
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public elements should be preserved
        assert "def public_method(self):" in result
        assert "def public_property(self):" in result
        
        # Private elements should be removed
        assert "def _private_method(self):" not in result
        assert "def _private_property(self):" not in result
    
    def test_no_functions_or_classes(self):
        """Test file with no functions or classes."""
        code = '''# Just some constants
PI = 3.14159
MAX_SIZE = 1000

# And some imports
import os
import sys
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Should be preserved since there are no private elements to filter
        assert "PI = 3.14159" in result
        assert "import os" in result
        assert meta.get("code.removed.private_elements", 0) == 0
    
    def test_combined_public_api_and_comment_filtering(self):
        """Test combining public API filtering with comment processing."""
        # Упрощенный тест без overlapping edits
        code = '''def public_function():
    """Public function docstring."""
    return "public"

def _private_function():
    """Private function docstring."""  
    return "private"
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            public_api_only=True,
            comment_policy="keep_doc"
        )
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public function and its docstring should be preserved
        assert "def public_function():" in result
        assert '"""Public function docstring."""' in result
        
        # Private function should be removed entirely
        assert "def _private_function():" not in result
        assert '"""Private function docstring."""' not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
