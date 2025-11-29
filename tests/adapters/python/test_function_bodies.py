"""
Tests for function body optimization in Python adapter.
"""

from lg.adapters.python import PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestPythonFunctionBodyOptimization:
    """Test function body stripping for Python code."""
    
    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(do_function_bodies))
        
        # Check that functions were processed
        assert meta.get("python.removed.function_body", 0) == 1
        assert meta.get("python.removed.method_body", 0) == 3
        assert "# … method body omitted" in result
        assert "# … function body omitted" in result
        
        # Golden file test
        assert_golden_match(result, "function_bodies", "basic_strip")
    
    def test_large_only_function_stripping(self, do_function_bodies):
        """Test stripping only large functions."""
        adapter = make_adapter(PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=3
            )
        ))
        
        result, meta = adapter.process(lctx(do_function_bodies))
        
        # Should have fewer removals than basic test
        assert_golden_match(result, "function_bodies", "large_only_strip")
    
    def test_no_stripping(self, do_function_bodies):
        """Test with stripping disabled."""
        adapter = make_adapter(PythonCfg(strip_function_bodies=False))
        
        result, meta = adapter.process(lctx(do_function_bodies))
        
        # No functions should be removed
        assert meta.get("python.removed.function_body", 0) == 0
        assert meta.get("python.removed.method_bodies", 0) == 0
        # Result should be close to original (may have minor whitespace changes)
        assert "def add(self, a: int, b: int) -> int:" in result
        assert "result = a + b" in result
    
    def test_public_only_function_stripping(self):
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
        
        function_config = FunctionBodyConfig(mode="public_only")
        adapter = make_adapter(PythonCfg(strip_function_bodies=function_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Public function body should be stripped
        assert "def public_function():" in result
        assert "# … function body omitted" in result
        assert "x = 1" not in result
        
        # Private function body should be preserved (it's not public)
        assert "def _private_function():" in result
        assert "a = 10" in result
        
        assert meta.get("python.removed.function_body", 0) == 1
    
    def test_non_public_function_stripping(self):
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
        
        function_config = FunctionBodyConfig(mode="non_public")
        adapter = make_adapter(PythonCfg(strip_function_bodies=function_config))
        
        result, meta = adapter.process(lctx(code))
        
        # Public function body should be preserved
        assert "def public_function():" in result
        assert "x = 1" in result
        
        # Private function body should be stripped
        assert "def _private_function():" in result
        assert "# … function body omitted" in result
        assert "a = 10" not in result
        
        assert meta.get("python.removed.function_body", 0) == 1


class TestPythonFunctionBodyEdgeCases:
    """Test edge cases for Python function body optimization."""
    
    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''def simple(): return 42

def complex():
    x = 1
    y = 2
    return x + y
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Single-line function should not be stripped (important for arrow-like functions)
        assert "def simple(): return 42" in result
        
        # Multi-line function should be stripped
        assert "def complex():" in result
        assert "# … function body omitted" in result
        assert "x = 1" not in result
    
    def test_nested_functions(self):
        """Test handling of nested functions."""
        code = '''def outer():
    """Outer function."""
    def inner():
        """Inner function."""
        return "inner"
    
    result = inner()
    return f"outer: {result}"
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Outer function should be preserved with docstring
        assert "def outer():" in result
        assert '"""Outer function."""' in result
        # Inner function should also be processed
        assert "def inner():" not in result
        assert '"""Inner function."""' not in result
        # At least some optimization should occur
        assert "# … function body omitted (7 lines)" in result
        assert meta.get("python.removed.function_body", 0) == 2
    
    def test_class_methods(self):
        """Test handling of class methods specifically."""
        code = '''class TestClass:
    def __init__(self):
        # Multi-line constructor
        self.value = 42
        self.initialized = True
    
    def public_method(self):
        # Multi-line method
        result = self.value
        return result
    
    def _private_method(self):
        # Multi-line private method
        temp = self.value * 2
        return temp
    
    @property
    def value_property(self):
        # Multi-line property
        val = self.value
        return val
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # All method bodies should be stripped
        assert "def __init__(self):" in result
        assert "def public_method(self):" in result
        assert "def _private_method(self):" in result
        assert "def value_property(self):" in result

        # Bodies should be replaced with placeholders
        assert "# … method body omitted" in result
        assert "self.initialized = True" not in result
        assert "result = self.value" not in result
        
        assert meta.get("python.removed.method_body", 0) == 4


class TestPythonDocstringPreservation:
    """Test preservation of docstrings when stripping function bodies."""
    
    def test_function_with_docstring_preserved(self):
        """Test that function docstrings are preserved when bodies are stripped."""
        code = '''def calculate_sum(a, b):
    """Calculate the sum of two numbers.
    
    Args:
        a (int): First number
        b (int): Second number
        
    Returns:
        int: Sum of a and b
    """
    # This is a comment
    result = a + b
    print(f"Sum: {result}")
    return result
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Function signature should be preserved
        assert "def calculate_sum(a, b):" in result
        
        # Docstring should be preserved completely
        assert '"""Calculate the sum of two numbers.' in result
        assert 'Args:' in result
        assert 'Returns:' in result
        
        # Function body should be removed
        assert "result = a + b" not in result
        assert "print(f" not in result
        assert "return result" not in result
        
        # Should have placeholder for removed body
        assert "# … function body omitted" in result
        
        # Should report function removal
        assert meta.get("python.removed.function_body", 0) == 1
    
    def test_method_with_docstring_preserved(self):
        """Test that method docstrings are preserved when bodies are stripped."""
        code = '''class Calculator:
    def multiply(self, a, b):
        """Multiply two numbers together.
        
        This method performs multiplication operation.
        """
        temp = a * b
        self.history.append(f"multiply({a}, {b}) = {temp}")
        return temp
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Method signature should be preserved
        assert "def multiply(self, a, b):" in result
        
        # Docstring should be preserved
        assert '"""Multiply two numbers together.' in result
        assert 'This method performs multiplication operation.' in result
        
        # Method body should be removed
        assert "temp = a * b" not in result
        assert "self.history.append" not in result
        assert "return temp" not in result
        
        # Should have placeholder for removed body
        assert "# … method body omitted" in result

        # Should report method removal
        assert meta.get("python.removed.method_body", 0) == 1
    
    def test_function_without_docstring_full_removal(self):
        """Test that functions without docstrings have bodies fully removed."""
        code = '''def simple_function():
    # Just a comment, no docstring
    x = 1
    y = 2
    return x + y
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Function signature should be preserved
        assert "def simple_function():" in result
        
        # Everything else should be removed
        assert "# Just a comment" not in result
        assert "x = 1" not in result
        assert "return x + y" not in result
        
        # Should have placeholder
        assert "# … function body omitted" in result
        
        assert meta.get("python.removed.function_body", 0) == 1
    
    def test_different_docstring_formats(self):
        """Test preservation of different docstring formats."""
        code = '''def func1():
    """Single line docstring."""
    return "result1"

def func2():
    """
    Multi-line docstring
    with additional details.
    """
    return "result2"

def func3():
    'Single quotes docstring.'
    return "result3"
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # All function signatures should be preserved
        assert "def func1():" in result
        assert "def func2():" in result  
        assert "def func3():" in result
        
        # All docstrings should be preserved
        assert '"""Single line docstring."""' in result
        assert '"""' in result and 'Multi-line docstring' in result
        assert "'Single quotes docstring.'" in result
        
        # All function bodies should be removed
        assert 'return "result1"' not in result
        assert 'return "result2"' not in result
        assert 'return "result3"' not in result
        
        assert meta.get("python.removed.function_body", 0) == 3
    
    def test_mixed_functions_with_without_docstrings(self):
        """Test mixed functions - some with docstrings, some without."""
        code = '''def documented_function():
    """This function has documentation."""
    complex_logic = True
    if complex_logic:
        return "documented"
    return "fallback"

def undocumented_function():
    # No docstring here
    simple_return = "undocumented"
    return simple_return
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Both function signatures should be preserved
        assert "def documented_function():" in result
        assert "def undocumented_function():" in result
        
        # Only the docstring should be preserved
        assert '"""This function has documentation."""' in result
        assert "# No docstring here" not in result
        
        # All logic should be removed
        assert "complex_logic = True" not in result
        assert "simple_return" not in result
        assert 'return "documented"' not in result
        assert 'return "undocumented"' not in result
        
        # Should have placeholders
        assert "# … function body omitted" in result
        
        assert meta.get("python.removed.function_body", 0) == 2
    
    def test_docstring_only_function(self):
        """Test function that contains only a docstring."""
        code = '''def docstring_only():
    """This function only has a docstring and nothing else."""
    pass
'''
        
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx(code))
        
        # Function should be preserved
        assert "def docstring_only():" in result
        
        # Docstring should be preserved
        assert '"""This function only has a docstring and nothing else."""' in result
        
        # pass statement should be removed (after docstring)
        # The function should either keep the docstring only, and add minimal placeholder
        assert "pass" not in result
        assert "# … function body omitted" in result