"""
Tests for public API filtering in Python adapter.
"""
import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from .conftest import lctx_py, do_public_api, assert_golden_match


class TestPythonPublicApiFiltering:
    """Test public API filtering for Python code."""
    
    def test_basic_public_api_filtering(self, do_public_api):
        """Test basic public API filtering."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(do_public_api))
        
        # Private elements should be removed
        assert meta.get("code.removed.functions", 0) == 3
        assert meta.get("code.removed.methods", 0) == 6
        assert meta.get("code.removed.classes", 0) == 2

        # Public elements should be preserved
        assert "def public_function(" in result
        assert "class PublicClass:" in result
        assert "def public_method(" in result
        
        # Private elements should be removed
        assert "def _private_function(" not in result
        assert "def _protected_method(" not in result
        assert "def __private_method(" not in result
        
        assert_golden_match(result, "public_api", "basic")

    @pytest.mark.skip(reason="Skipping this test for now.")
    def test_underscore_naming_conventions(self):
        """Test Python underscore naming conventions."""
        code = '''
def public_function():
    return "public"

def _protected_function():
    return "protected"

def __private_function():
    return "private"

def __special_method__(self):
    return "special"

class PublicClass:
    def public_method(self):
        return "public"
    
    def _protected_method(self):
        return "protected"
    
    def __private_method(self):
        return "private"
        
    def __init__(self):
        pass
        
    def __str__(self):
        return "special"

class _PrivateClass:
    pass

PUBLIC_VAR = "public"
_PROTECTED_VAR = "protected"
__PRIVATE_VAR = "private"
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public elements should be preserved
        assert "def public_function():" in result
        assert "class PublicClass:" in result
        assert "def public_method(self):" in result
        assert "PUBLIC_VAR = " in result
        
        # Special methods should be preserved (dunder methods)
        assert "def __init__(self):" in result
        assert "def __str__(self):" in result
        assert "def __special_method__(self):" in result
        
        # Private/protected elements should be removed
        assert "def _protected_function():" not in result
        assert "def __private_function():" not in result
        assert "class _PrivateClass:" not in result
        assert "_PROTECTED_VAR = " not in result
        assert "__PRIVATE_VAR = " not in result
    
    def test_module_level_guard_preservation(self):
        """Test that if __name__ == '__main__' is preserved."""
        code = '''
def public_function():
    return "public"

def _private_function():
    return "private"

if __name__ == "__main__":
    # This should be preserved as it's a standard pattern
    print(public_function())
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public function should be preserved
        assert "def public_function():" in result
        
        # Private function should be removed
        assert "def _private_function():" not in result
        
        # Main guard should be preserved
        assert 'if __name__ == "__main__":' in result


class TestPythonPublicApiEdgeCases:
    """Test edge cases for Python public API filtering."""
    
    def test_nested_classes_and_functions(self):
        """Test nested classes and functions filtering."""
        code = '''
class PublicOuter:
    def public_method(self):
        return "public"
    
    def _private_method(self):
        return "private"
    
    class PublicInner:
        def inner_public(self):
            return "inner public"
    
    class _PrivateInner:
        def inner_method(self):
            return "inner private"

def public_outer():
    def inner_function():
        return "nested"
    return inner_function()
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public outer elements should be preserved
        assert "class PublicOuter:" in result
        assert "def public_method(self):" in result
        assert "class PublicInner:" in result
        
        # Private nested elements should be removed
        assert "def _private_method(self):" not in result
        assert "class _PrivateInner:" not in result
    
    def test_property_and_descriptor_methods(self):
        """Test property and descriptor methods."""
        code = '''
class DataClass:
    @property
    def public_property(self):
        return self._value
    
    @property
    def _private_property(self):
        return self._private_value
    
    @public_property.setter
    def public_property(self, value):
        self._value = value
    
    @staticmethod
    def public_static():
        return "static"
    
    @staticmethod
    def _private_static():
        return "private static"
    
    @classmethod
    def public_class_method(cls):
        return cls()
    
    @classmethod
    def _private_class_method(cls):
        return cls()
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(public_api_only=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public properties and methods should be preserved
        assert "def public_property(self):" in result
        assert "def public_static():" in result
        assert "def public_class_method(cls):" in result
        
        # Private properties and methods should be removed
        assert "def _private_property(self):" not in result
        assert "def _private_static():" not in result
        assert "def _private_class_method(cls):" not in result
