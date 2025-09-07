"""
Complex integration tests for TypeScript adapter.
Tests combining multiple optimization types and edge cases.
"""

from lg.adapters.code_model import ImportConfig, LiteralConfig, FieldConfig
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from .conftest import lctx_ts, lctx, assert_golden_match, do_complex


class TestTypeScriptComplexOptimizations:
    """Test complex combinations of optimizations for TypeScript code."""
    
    def test_moderate_optimization_combo(self, do_complex):
        """Test moderate combination of optimizations."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            comment_policy="keep_doc",
            literal_config=LiteralConfig(
                max_string_length=100,
                max_array_elements=5
            ),
            import_config=ImportConfig(policy="external_only"),
            field_config=FieldConfig(remove_trivial_constructors=True)
        )
        
        result, meta = adapter.process(lctx_ts(do_complex))
        
        # Multiple optimizations should be applied
        assert meta.get("code.removed.comments", 0) > 0 or meta.get("code.removed.literal_data", 0) > 0
        assert meta.get("code.removed.imports", 0) > 0 or meta.get("code.removed.trivial_constructors", 0) > 0
        
        # JSDoc should be preserved
        assert "/**" in result
        # External imports should remain
        assert "import" in result and ("react" in result or "lodash" in result)
        
        assert_golden_match(result, "complex", "moderate_combo")
    
    def test_aggressive_optimization_combo(self, do_complex):
        """Test aggressive combination of optimizations."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            comment_policy="keep_first_sentence",
            literal_config=LiteralConfig(
                max_string_length=50,
                max_array_elements=3,
                max_object_properties=4,
                collapse_threshold=100
            ),
            import_config=ImportConfig(
                policy="external_only",
                max_line_length=80,
                max_imports_per_line=3
            ),
            field_config=FieldConfig(
                remove_trivial_constructors=True,
                remove_trivial_getters=True,
                remove_trivial_setters=True
            ),
            public_api_only=True
        )
        
        result, meta = adapter.process(lctx_ts(do_complex))
        
        # Aggressive optimizations should show significant changes
        total_removed = (
            meta.get("code.removed.comments", 0) +
            meta.get("code.removed.literal_data", 0) +
            meta.get("code.removed.imports", 0) +
            meta.get("code.removed.trivial_constructors", 0) +
            meta.get("code.removed.private_elements", 0)
        )
        assert total_removed > 0
        
        # Only public API should remain
        assert "export" in result
        # Comments should be truncated to first sentence
        assert "." in result  # First sentence ending
        
        assert_golden_match(result, "complex", "aggressive_combo")
