"""
Tests for literal trimming in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_py, do_literals, assert_golden_match


class TestPythonLiteralOptimization:
    """Test literal data optimization for Python code."""
    
    def test_basic_literal_trimming(self, do_literals):
        """Test basic literal trimming with default settings."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=True)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Should have processed some literals
        assert meta.get("code.removed.literals", 0) > 0
        assert meta.get("code.placeholders", 0) > 0
        
        # Long string should be trimmed
        assert "This is a very long string that contains a lot of text" not in result
        assert "# … string data" in result or "… string data" in result
        
        # Large list should be trimmed
        long_list_items = '"item_1", "item_2", "item_3", "item_4", "item_5"'
        assert long_list_items not in result or "… array data" in result
        
        assert_golden_match(result, "literals", "basic_trimming")
    
    def test_string_length_limiting(self, do_literals):
        """Test string literal length limiting."""
        literal_config = LiteralConfig(
            max_string_length=50,
            max_array_elements=10,
            max_object_properties=5
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Long strings should be truncated
        assert meta.get("code.removed.literals", 0) > 0
        # Short strings should be preserved
        assert 'SHORT_STRING = "hello"' in result
        
        assert_golden_match(result, "literals", "string_length_limiting")
    
    def test_array_element_limiting(self, do_literals):
        """Test array element count limiting."""
        literal_config = LiteralConfig(max_array_elements=5)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Large arrays should be summarized
        assert meta.get("code.removed.literals", 0) > 0
        # Small arrays should be preserved
        assert "[1, 2, 3]" in result or "self.small_list = [1, 2, 3]" in result
        
        assert_golden_match(result, "literals", "array_limiting")
    
    def test_object_property_limiting(self, do_literals):
        """Test object property count limiting."""
        literal_config = LiteralConfig(max_object_properties=3)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Large objects should be summarized
        assert meta.get("code.removed.literals", 0) > 0
        # Small objects should be preserved
        assert '"name": "test", "value": 42' in result or '{"name": "test", "value": 42}' in result
        
        assert_golden_match(result, "literals", "object_limiting")
    
    def test_multiline_literal_limiting(self, do_literals):
        """Test multiline literal limiting.""" 
        literal_config = LiteralConfig(max_literal_lines=5)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Multiline literals should be collapsed
        assert meta.get("code.removed.literals", 0) > 0
        assert "# … " in result or "… " in result
        
        assert_golden_match(result, "literals", "multiline_limiting")
    
    def test_size_based_collapsing(self, do_literals):
        """Test size-based literal collapsing."""
        literal_config = LiteralConfig(collapse_threshold=200)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(do_literals))
        
        # Large literals should be collapsed based on byte size
        assert meta.get("code.removed.literals", 0) > 0
        assert "# … " in result or "… " in result
        
        assert_golden_match(result, "literals", "size_based_collapsing")
    
    def test_preserve_small_literals(self):
        """Test that small literals are preserved."""
        code = '''
# Small literals that should be preserved
name = "test"
count = 42
flags = [True, False]
config = {"debug": True, "level": 1}
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=True)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Small literals should be preserved
        assert 'name = "test"' in result
        assert 'count = 42' in result
        assert 'flags = [True, False]' in result
        assert '{"debug": True, "level": 1}' in result
        
        # No literals should be processed if they're all small
        assert meta.get("code.removed.literals", 0) == 0
    
    def test_docstring_exclusion(self):
        """Test that docstrings are not processed as string literals."""
        code = '''def function():
    """This is a very long docstring that should not be processed as a string literal even though it exceeds the maximum string length threshold."""
    very_long_string = "This is a very long regular string that should be processed as a literal and potentially trimmed based on the configuration settings."
    return very_long_string
'''
        
        literal_config = LiteralConfig(max_string_length=50)
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Docstring should be preserved
        assert '"""This is a very long docstring' in result
        # Regular string should be trimmed
        assert "This is a very long regular string that should be..." in result or "… string data" in result


class TestPythonLiteralEdgeCases:
    """Test edge cases for Python literal optimization."""
    
    def test_nested_data_structures(self):
        """Test handling of deeply nested data structures."""
        code = '''
nested = {
    "level1": {
        "level2": {
            "level3": [
                {"id": 1, "data": "item1"},
                {"id": 2, "data": "item2"},
                {"id": 3, "data": "item3"}
            ]
        }
    }
}
'''
        
        literal_config = LiteralConfig(
            max_object_properties=2,
            max_array_elements=2
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Nested structure should be processed
        assert meta.get("code.removed.literals", 0) > 0
        assert "# … " in result or "… " in result
    
    def test_mixed_literal_types(self):
        """Test handling of mixed literal types in same context."""
        code = '''
def process():
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Array
    config = {"a": 1, "b": 2, "c": 3, "d": 4}  # Object
    message = "A very long message that should be trimmed"  # String
    return data, config, message
'''
        
        literal_config = LiteralConfig(
            max_array_elements=5,
            max_object_properties=2,
            max_string_length=20
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # All literal types should be processed
        assert meta.get("code.removed.literals", 0) >= 3
        assert "# … " in result or "… " in result
    
    def test_literal_in_function_arguments(self):
        """Test literals used as function arguments."""
        code = '''
result = some_function([
    "item1", "item2", "item3", "item4", "item5",
    "item6", "item7", "item8", "item9", "item10"
], {
    "setting1": "value1",
    "setting2": "value2", 
    "setting3": "value3",
    "setting4": "value4"
})
'''
        
        literal_config = LiteralConfig(
            max_array_elements=3,
            max_object_properties=2
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Function argument literals should be processed
        assert meta.get("code.removed.literals", 0) > 0
    
    def test_set_and_tuple_literals(self):
        """Test handling of set and tuple literals."""
        code = '''
tags = {"python", "javascript", "typescript", "java", "csharp", "cpp"}
coordinates = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
'''
        
        literal_config = LiteralConfig(max_array_elements=3)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Sets and tuples should be processed like arrays
        assert meta.get("code.removed.literals", 0) > 0
