"""
Complex integration tests for Python adapter.
Tests combining multiple optimization types and edge cases.
"""

from lg.adapters.code_model import LiteralConfig, FieldConfig, ImportConfig, CommentConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from .conftest import assert_golden_match, lctx_py, do_complex


class TestPythonComplexOptimization:
    """Test complex combinations of optimizations for Python code."""
    
    def test_full_optimization_pipeline(self, do_complex):
        """Test full optimization pipeline with all types enabled."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            # Enable all optimizations with moderate settings
            strip_function_bodies=True,
            comment_policy="keep_doc",
            strip_literals=LiteralConfig(max_string_length=100, max_array_elements=10),
            imports=ImportConfig(policy="external_only"),
            public_api_only=True,
            fields=FieldConfig(strip_trivial_constructors=True, strip_trivial_accessors=True)
        )
        
        result, meta = adapter.process(lctx_py(do_complex))
        
        # Should have multiple types of optimizations applied
        optimization_count = 0
        if meta.get("code.removed.functions", 0) > 0:
            optimization_count += 1
        if meta.get("code.removed.comments", 0) > 0:
            optimization_count += 1
        if meta.get("code.removed.literals", 0) > 0:
            optimization_count += 1
        if meta.get("code.removed.imports", 0) > 0:
            optimization_count += 1
        if meta.get("code.removed.private_elements", 0) > 0:
            optimization_count += 1
        
        # Expect at least 3 different types of optimizations
        assert optimization_count >= 3
        
        assert_golden_match(result, "complex", "full_pipeline")
    
    def test_balanced_optimization(self, do_complex):
        """Test balanced optimization that preserves enough information."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            # Balanced settings to avoid over-optimization
            strip_function_bodies=False,  # Keep function bodies for this test
            comment_policy="keep_doc",
            strip_literals=LiteralConfig(max_array_elements=15),  # More lenient
            imports=ImportConfig(policy="summarize_long", max_items_before_summary=8),
            public_api_only=False,  # Keep private elements for this test
            fields=FieldConfig(strip_trivial_constructors=True)
        )
        
        result, meta = adapter.process(lctx_py(do_complex))
        
        # Should have some optimizations but preserve key information
        assert meta.get("code.removed.constructors", 0) > 0  # Field optimization
        assert "def processDataWithAnalytics" in result  # Function signatures preserved
        assert "class ComplexOptimizationDemo:" in result  # Class structure preserved
        
        assert_golden_match(result, "complex", "balanced_optimization")
    
    def test_non_interfering_optimizations(self, do_complex):
        """Test that optimizations don't interfere with each other."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            # Configure optimizations to target different parts
            strip_function_bodies=True,  # Targets method bodies
            comment_policy=CommentConfig(policy="strip_all", keep_annotations=["TODO"]),
            strip_literals=True,  # Targets data literals
            imports=ImportConfig(policy="external_only"),  # Targets import statements
            public_api_only=False,  # Don't remove whole elements
            fields=FieldConfig(strip_trivial_constructors=True)  # Targets constructors
        )
        
        result, meta = adapter.process(lctx_py(do_complex))
        
        # Each optimization should contribute independently
        assert meta.get("code.removed.functions", 0) > 0  # Function body optimization
        assert meta.get("code.removed.comments", 0) > 0  # Comment optimization
        assert meta.get("code.removed.literals", 0) > 0  # Literal optimization
        assert meta.get("code.removed.imports", 0) > 0  # Import optimization
        assert meta.get("code.removed.constructors", 0) > 0  # Field optimization
        
        # Should preserve TODO comments (selective comment policy)
        assert "TODO:" in result
        
        assert_golden_match(result, "complex", "non_interfering")


class TestPythonOptimizationInteractions:
    """Test interactions between different optimization types."""
    
    def test_public_api_with_function_bodies(self, do_complex):
        """Test public API filtering combined with function body optimization."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            public_api_only=True,  # Remove private elements first
            strip_function_bodies=True  # Then optimize remaining function bodies
        )
        
        result, meta = adapter.process(lctx_py(do_complex))
        
        # Private elements should be removed by public API filter
        assert meta.get("code.removed.private_elements", 0) > 0
        
        # Remaining public functions should have body optimization
        assert meta.get("code.removed.functions", 0) > 0 or meta.get("code.removed.methods", 0) > 0
        
        # Private function should not appear (removed by public API filter)
        assert "def processInternalData(" not in result
        
        # Public function should appear but with optimized body
        assert "def processDataWithAnalytics(" in result
        assert "# … " in result or "… method omitted" in result
    
    def test_comment_preservation_in_optimized_functions(self):
        """Test that comment optimization doesn't interfere with function body optimization."""
        code = '''
def documented_function():
    """Important function documentation.
    
    This should be preserved even when function body is stripped.
    """
    # Regular comment that might be stripped
    result = process_data()
    # TODO: Optimize this logic
    return result
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            strip_function_bodies=True,  # Remove function body but keep docstring
            comment_policy=CommentConfig(policy="keep_doc", keep_annotations=["TODO"])
        )
        
        result, meta = adapter.process(lctx_py(code))
        
        # Function signature and docstring should be preserved
        assert "def documented_function():" in result
        assert '"""Important function documentation.' in result
        
        # Function body should be optimized
        assert "result = process_data()" not in result
        assert "# … " in result or "… body omitted" in result
        
        # TODO comment preservation depends on implementation details
        # (may be inside the removed function body)
        
    def test_minimal_optimization_for_debugging(self, do_complex):
        """Test minimal optimization settings for debugging purposes."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            # Very conservative settings
            strip_function_bodies=False,
            comment_policy="keep_all",
            strip_literals=False,
            imports=ImportConfig(policy="keep_all"),
            public_api_only=False,
            fields=FieldConfig(strip_trivial_constructors=False, strip_trivial_accessors=False)
        )
        
        result, meta = adapter.process(lctx_py(do_complex))
        
        # Minimal changes should be made
        total_removals = (
            meta.get("code.removed.functions", 0) +
            meta.get("code.removed.comments", 0) +
            meta.get("code.removed.literals", 0) +
            meta.get("code.removed.imports", 0) +
            meta.get("code.removed.constructors", 0) +
            meta.get("code.removed.private_elements", 0)
        )
        
        # Should have very few or no removals
        assert total_removals <= 1  # Allow for minor optimizations
        
        # Most content should be preserved
        assert "def processDataWithAnalytics(" in result
        assert "# Comment that should be handled" in result
        assert "import os" in result
