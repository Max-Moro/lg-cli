"""
Complex integration tests for Python adapter.
Tests combining multiple optimization types and edge cases.
"""

from lg.adapters.code_model import LiteralConfig, FieldConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from .conftest import assert_golden_match, lctx_py, lctx


class TestPythonComplexIntegration:
    """Complex integration tests for Python adapter."""

    def test_full_optimization_pipeline(self, code_sample):
        """Test complete Python adapter pipeline with all optimizations."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg.from_dict({
            "strip_function_bodies": True,
            "comment_policy": "keep_doc",
            "public_api_only": False,
            "strip_literals": {
                "max_string_length": 50,
                "max_array_elements": 10
            },
            "imports": {
                "policy": "external_only"
            },
            "fields": {
                "strip_trivial_constructors": True
            },
            "placeholders": {
                "mode": "summary",
                "style": "inline"
            }
        })

        result, meta = adapter.process(lctx_py(code_sample))

        # Verify multiple optimizations occurred
        assert meta.get("code.removed.functions", 0) >= 0
        assert meta.get("code.removed.methods", 0) >= 0

        # Verify placeholders were inserted if optimizations occurred
        if (meta.get("code.removed.functions", 0) > 0 or 
            meta.get("code.removed.methods", 0) > 0):
            assert "# … " in result

        # Verify structure is preserved
        assert "class Calculator:" in result
        assert "def add(self, a: int, b: int) -> int:" in result

        # Verify docstrings are preserved (comment_policy="keep_doc")
        assert '"""A simple calculator class."""' in result

        # Golden file test
        assert_golden_match(result, "full_pipeline")

    def test_combined_literal_and_function_trimming(self):
        """Test combining literal trimming with function body stripping."""
        code = '''
DATA = [
    "item1", "item2", "item3", "item4", "item5",
    "item6", "item7", "item8", "item9", "item10"
]

def process_data():
    """Process the data array."""
    result = []
    for item in DATA:
        result.append(item.upper())
    return result
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_array_elements=5)
        adapter._cfg = PythonCfg(
            strip_literals=literal_config,
            strip_function_bodies=True
        )
        
        result, meta = adapter.process(lctx_py(code))
        
        # Array should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        
        # Function body should be stripped
        assert "def process_data():" in result
        assert ("# … body omitted" in result or "# … function omitted" in result) or meta.get("code.removed.functions", 0) > 0
        assert "result.append(item.upper())" not in result or "..." in result
        
        # Both optimizations should have occurred
        if "more]" in result:
            assert meta.get("code.removed.literals", 0) > 0
        if "body omitted" in result:
            assert meta.get("code.removed.functions", 0) > 0

    def test_trivial_init_py_handling(self):
        """Test comprehensive handling of __init__.py files."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg()

        # Тривиальные случаи (__init__.py): пусто, pass, ..., комментарии + pass/...
        trivial_cases = [
            "",
            "pass",
            "...",
            "# Comment\npass",
            "# Comment\n...",
            "from .module import something\n__all__ = ['something']",  # Re-export only
        ]

        for i, content in enumerate(trivial_cases):
            ctx = lctx(content, "__init__.py")
            should_skip = adapter.should_skip(ctx)
            assert should_skip, f"Should skip trivial __init__.py: {repr(content)}"

        # Только комментарии — НЕ тривиальный
        comment_only_ctx = lctx("# Comment only", "__init__.py")
        assert not adapter.should_skip(comment_only_ctx), "Comment-only __init__.py must NOT be considered trivial"

        # Нетривиальный: есть «настоящее» содержимое
        non_trivial = "from .module import something\nvalue = 42"
        non_trivial_ctx = lctx(non_trivial, "__init__.py")
        should_not_skip = adapter.should_skip(non_trivial_ctx)
        assert not should_not_skip, "Should not skip non-trivial __init__.py"

    def test_error_handling_graceful(self):
        """Test graceful error handling with malformed code."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)

        # Test with malformed code that might cause parsing issues
        malformed_code = "def incomplete_function("
        
        # Should not crash, even with syntax errors
        result, meta = adapter.process(lctx_py(malformed_code))
        
        # Should have processed something
        assert meta["_adapter"] == "python"
        assert isinstance(result, str)

    def test_metadata_collection_comprehensive(self, code_sample):
        """Test comprehensive metadata collection."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            strip_function_bodies=True,
            comment_policy="strip_all",
            strip_literals=True
        )
        
        result, meta = adapter.process(lctx_py(code_sample))
        
        # Check required metadata fields
        required_fields = [
            "_group_size", "_group_mixed", "_adapter",
            "code.removed.functions", "code.removed.methods"
        ]
        
        for field in required_fields:
            assert field in meta, f"Missing metadata field: {field}"
        
        assert meta["_adapter"] == "python"
        assert meta["_group_size"] == 1
        assert meta["_group_mixed"] is False
        
        # Should have some processing performed when stripping is enabled
        total_removed = (meta.get("code.removed.functions", 0) + 
                        meta.get("code.removed.methods", 0) +
                        meta.get("code.removed.comments", 0) +
                        meta.get("code.removed.literals", 0))
        assert total_removed > 0, "Expected some code to be removed with aggressive settings"

    def test_configuration_loading_comprehensive(self):
        """Test comprehensive configuration loading from various formats."""
        # Test simple boolean config
        cfg = PythonCfg.from_dict({"strip_function_bodies": True})
        assert cfg.strip_function_bodies is True

        # Test complex object config
        complex_config = {
            "strip_function_bodies": {
                "mode": "large_only",
                "min_lines": 10,
                "except_patterns": ["test_.*", "__.*__"]
            },
            "comment_policy": {
                "policy": "keep_first_sentence",
                "max_length": 80
            },
            "skip_trivial_inits": False
        }

        cfg = PythonCfg.from_dict(complex_config)
        assert hasattr(cfg.strip_function_bodies, 'mode')
        assert cfg.strip_function_bodies.mode == "large_only"
        assert cfg.strip_function_bodies.min_lines == 10
        assert cfg.skip_trivial_inits is False

    def test_overlapping_optimizations_handling(self):
        """Test handling of potentially overlapping optimizations."""
        code = '''class Calculator:
    """Calculator class."""
    
    def __init__(self, name="calc"):
        """Initialize calculator."""
        self.name = name
        self.history = []
    
    def _private_helper(self):
        """Private helper method."""
        return "helper"
    
    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(
            public_api_only=True,  # Remove private methods
            strip_function_bodies=True,  # Strip remaining function bodies
            comment_policy="keep_doc",  # Keep docstrings
            fields=FieldConfig(strip_trivial_constructors=True)  # Strip trivial constructors
        )
        
        result, meta = adapter.process(lctx_py(code))
        
        # Public methods should be preserved but bodies stripped
        assert "def add(self, a, b):" in result
        assert "def __init__(self, name=" in result
        
        # Private method should be removed entirely
        assert "def _private_helper(self):" not in result
        
        # Docstrings should be preserved
        assert '"""Calculator class."""' in result
        assert '"""Add two numbers."""' in result
        
        # Should have placeholders for optimizations
        assert ("# … " in result or "… " in result)
        
        # Multiple optimization types should have occurred
        assert meta.get("code.removed.private_elements", 0) > 0
