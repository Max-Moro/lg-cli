"""
Tests for public API filtering in Python adapter.
"""

from lg.adapters.python import PythonCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestPythonPublicApiFiltering:
    """Test public API filtering for Python code."""
    
    def test_basic_public_api_filtering(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(do_public_api))
        
        # Private elements should be removed
        assert meta.get("python.removed.function", 0) == 3
        assert meta.get("python.removed.method", 0) == 7
        assert meta.get("python.removed.class", 0) == 3
        assert meta.get("python.removed.variable", 0) == 2

        # Public elements should be preserved
        assert "def public_function(" in result
        assert "class PublicClass:" in result
        assert "def public_method(" in result
        
        # Private elements should be removed
        assert "def _private_function(" not in result
        assert "def _protected_method(" not in result
        assert "def __private_method(" not in result
        
        assert_golden_match(result, "public_api", "basic")

    def test_decorator_handling_with_public_api(self, do_public_api):
        """Test that decorators are properly handled when removing private elements."""
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(do_public_api))
        
        # Check that decorators don't exist without their functions/classes
        lines = result.split('\n')
        
        # Look for hanging decorators (decorators followed by placeholder or nothing)
        hanging_decorators = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('@'):
                # This is a decorator line
                next_lines = []
                for j in range(i + 1, min(i + 5, len(lines))):  # Check next few lines
                    next_line = lines[j].strip()
                    if next_line:  # Non-empty line
                        next_lines.append(next_line)
                        break
                
                # If the next significant line is a placeholder, we have a hanging decorator
                if next_lines and next_lines[0].startswith('…'):
                    hanging_decorators.append((i, stripped, next_lines[0]))
        
        # Should not have any hanging decorators
        if hanging_decorators:
            print("Found hanging decorators:")
            for line_num, decorator, next_line in hanging_decorators:
                print(f"  Line {line_num}: {decorator} -> {next_line}")
        
        assert len(hanging_decorators) == 0, f"Found {len(hanging_decorators)} hanging decorators"
        
        # Specific checks for decorator combinations
        # @my_decorator should not appear without its class/function
        assert "@my_decorator" not in result and "class _PrivateDecoratedClass" not in result
        assert "@lru_cache" not in result and "_private_cached_function" not in result

        # Public decorated elements should preserve decorators
        if "@my_decorator" in result:
            # Should be followed by public elements
            my_decorator_pos = result.find("@my_decorator")
            public_class_pos = result.find("class PublicDecoratedClass")
            public_func_pos = result.find("def public_decorated_function")
            
            # At least one public element should follow @my_decorator
            assert public_class_pos > my_decorator_pos and public_func_pos > my_decorator_pos

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
        
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(code))
        
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
        
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(code))
        
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
        
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(code))
        
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
        
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Public properties and methods should be preserved
        assert "def public_property(self):" in result
        assert "def public_static():" in result
        assert "def public_class_method(cls):" in result
        
        # Private properties and methods should be removed
        assert "def _private_property(self):" not in result
        assert "def _private_static():" not in result
        assert "def _private_class_method(cls):" not in result

    def test_complex_decorator_scenarios(self):
        """Test complex decorator scenarios to ensure no hanging decorators."""
        code = '''
@property
@staticmethod  
def _private_multi_decorated():
    """This should be removed completely with all decorators."""
    return "private"

@lru_cache(maxsize=128)
def public_cached_function():
    """This should be preserved with decorator."""
    return "cached"

@property
def _private_property_decorated():
    """Private property should be removed with @property."""
    return "private"

class TestClass:
    @property
    @lru_cache(maxsize=64)
    def _private_method_multi(self):
        """Private method with multiple decorators - should remove all."""
        return "private"
    
    @staticmethod
    def public_static():
        """Public static method - should be preserved."""
        return "public"
'''
        
        adapter = make_adapter(PythonCfg(public_api_only=True))
        
        result, meta = adapter.process(lctx(code))
        
        # No hanging decorators check
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('@'):
                # Find next non-empty line
                next_content = None
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        next_content = lines[j].strip()
                        break
                
                # If next line is a placeholder, we have a hanging decorator
                if next_content and next_content.startswith('…'):
                    assert False, f"Hanging decorator found at line {i}: {line.strip()}"
        
        # Public elements should remain with decorators
        assert "@lru_cache" in result and "def public_cached_function" in result
        assert "def public_static" in result
        
        # Private decorated elements should be completely removed (no decorators left)
        assert "_private_multi_decorated" not in result
        assert "_private_property_decorated" not in result
