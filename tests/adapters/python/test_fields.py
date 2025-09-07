"""
Tests for field optimization in Python adapter.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FieldConfig
from .conftest import lctx_py, do_fields, assert_golden_match


class TestPythonFieldOptimization:
    """Test field optimization for Python code."""
    
    def test_trivial_constructor_stripping(self, do_fields):
        """Test stripping of trivial constructors."""
        field_config = FieldConfig(strip_trivial_constructors=True)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(do_fields))
        
        # Trivial constructors should be stripped
        assert meta.get("code.removed.constructors", 0) > 0
        assert "… trivial constructor omitted" in result or "… constructor omitted" in result
        
        assert_golden_match(result, "fields", "trivial_constructors")
    
    def test_trivial_property_stripping(self, do_fields):
        """Test stripping of trivial property accessors."""
        field_config = FieldConfig(strip_trivial_accessors=True)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(do_fields))
        
        # Trivial getters/setters should be stripped
        assert meta.get("code.removed.getters", 0) > 0 or meta.get("code.removed.setters", 0) > 0
        assert "… trivial getter omitted" in result or "… trivial setter omitted" in result
        
        assert_golden_match(result, "fields", "trivial_accessors")
    
    def test_combined_field_optimization(self, do_fields):
        """Test combined constructor and accessor optimization."""
        field_config = FieldConfig(
            strip_trivial_constructors=True,
            strip_trivial_accessors=True
        )
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(do_fields))
        
        # Both types should be optimized
        assert meta.get("code.removed.constructors", 0) > 0
        assert (meta.get("code.removed.getters", 0) > 0 or 
                meta.get("code.removed.setters", 0) > 0)
        
        assert_golden_match(result, "fields", "combined_optimization")


class TestPythonFieldEdgeCases:
    """Test edge cases for Python field optimization."""
    
    def test_non_trivial_preservation(self):
        """Test that non-trivial constructors are preserved."""
        code = '''
class ComplexClass:
    def __init__(self, data):
        if not data:
            raise ValueError("Data required")
        self.data = self._process(data)
        self.validated = True
    
    def _process(self, data):
        return data.upper()
'''
        
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(code))
        
        # Non-trivial constructor should be preserved
        assert "if not data:" in result
        assert "self.data = self._process(data)" in result
        assert meta.get("code.removed.constructors", 0) == 0
