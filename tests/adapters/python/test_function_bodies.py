"""
Tests for function body optimization in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_py, python_code_sample, assert_golden_match


class TestPythonFunctionBodyOptimization:
    """Test function body stripping for Python code."""
    
    def test_basic_function_stripping(self, python_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(lctx_py(python_code_sample))
        
        # Check that functions were processed
        assert meta["code.removed.functions"] > 0
        assert meta["code.removed.methods"] > 0
        assert "# … method omitted" in result or "# … body omitted" in result
        
        # Golden file test
        golden_file = tmp_path / "python_basic_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_large_only_function_stripping(self, python_code_sample, tmp_path):
        """Test stripping only large functions."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=3
            )
        )
        
        result, meta = adapter.process(lctx_py(python_code_sample))
        
        # Should have fewer removals than basic test
        golden_file = tmp_path / "python_large_only_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_no_stripping(self, python_code_sample):
        """Test with stripping disabled."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(lctx_py(python_code_sample))
        
        # No functions should be removed
        assert meta.get("code.removed.functions", 0) == 0
        assert meta.get("code.removed.methods", 0) == 0
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
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Single-line function should not be stripped (important for arrow-like functions)
        assert "def simple(): return 42" in result
        
        # Multi-line function should be stripped
        assert "def complex():" in result
        assert "# … body omitted" in result or "# … function omitted" in result
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
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Outer function body should be stripped
        assert "def outer():" in result
        assert "# … body omitted" in result or "# … function omitted" in result
        assert "def inner():" not in result  # Should be part of stripped body
    
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
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # All method bodies should be stripped
        assert "def __init__(self):" in result
        assert "def public_method(self):" in result
        assert "def _private_method(self):" in result
        assert "def value_property(self):" in result

        # Bodies should be replaced with placeholders
        assert "# … method omitted" in result or "# … body omitted" in result
        assert "self.initialized = True" not in result
        assert "result = self.value" not in result
        
        assert meta.get("code.removed.methods", 0) > 0
