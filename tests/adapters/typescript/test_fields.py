"""
Tests for field optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FieldConfig
from .conftest import lctx_ts, do_fields, assert_golden_match


class TestTypeScriptFieldOptimization:
    """Test field optimization for TypeScript code."""
    
    def test_trivial_constructor_removal(self, do_fields):
        """Test removal of trivial constructors."""
        field_config = FieldConfig(
            remove_trivial_constructors=True
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(field_config=field_config)
        
        result, meta = adapter.process(lctx_ts(do_fields))
        
        # Trivial constructors should be removed
        assert meta.get("code.removed.trivial_constructors", 0) > 0
        assert "… trivial constructor" in result or "…" in result
        
        assert_golden_match(result, "fields", "trivial_constructors")
    
    def test_getter_setter_removal(self, do_fields):
        """Test removal of trivial getters and setters."""
        field_config = FieldConfig(
            remove_trivial_getters=True,
            remove_trivial_setters=True
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(field_config=field_config)
        
        result, meta = adapter.process(lctx_ts(do_fields))
        
        # Trivial getters/setters should be removed
        assert meta.get("code.removed.trivial_getters", 0) > 0 or meta.get("code.removed.trivial_setters", 0) > 0
        assert "… getter/setter" in result or "…" in result
        
        assert_golden_match(result, "fields", "getters_setters")
    
    def test_combined_field_optimization(self, do_fields):
        """Test combined field optimization."""
        field_config = FieldConfig(
            remove_trivial_constructors=True,
            remove_trivial_getters=True,
            remove_trivial_setters=True,
            preserve_complex_logic=True
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(field_config=field_config)
        
        result, meta = adapter.process(lctx_ts(do_fields))
        
        # Multiple optimizations should be applied
        total_removed = (
            meta.get("code.removed.trivial_constructors", 0) +
            meta.get("code.removed.trivial_getters", 0) +
            meta.get("code.removed.trivial_setters", 0)
        )
        assert total_removed > 0
        
        assert_golden_match(result, "fields", "combined")
