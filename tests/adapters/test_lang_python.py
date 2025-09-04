"""
Tests for based Python adapter.
"""

import pytest
from lg.adapters.code_model import FunctionBodyConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from tests.adapters.conftest import assert_golden_match, create_temp_file


class TestPythonAdapter:
    """Test suite for Python adapter."""
    
    def test_basic_function_stripping(self, python_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        # Create lightweight context with sample code
        ctx = lctx(
            raw_text=python_code_sample,
        )
        
        result, meta = adapter.process(ctx)
        
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
        
        result, meta = adapter.process(python_code_sample, "py", group_size=1, mixed=False)
        
        # Should have fewer removals than basic test
        golden_file = tmp_path / "python_large_only_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_no_stripping(self, python_code_sample):
        """Test with stripping disabled."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(python_code_sample, "py", group_size=1, mixed=False)
        
        # No functions should be removed
        # Result should be close to original (may have minor whitespace changes)
        assert "def add(self, a: int, b: int) -> int:" in result
        assert "result = a + b" in result
    
    def test_trivial_init_py_skipping(self, tmp_path):
        """Test that trivial __init__.py files are skipped."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg()
        
        # Test various trivial __init__.py patterns
        trivial_cases = [
            "",
            "pass",
            "...",
            "# Comment only",
            "# Comment\npass",
            "# Comment\n...",
        ]
        
        for i, content in enumerate(trivial_cases):
            # Создаем контекст для __init__.py файла
            ctx = lctx(
                raw_text=content,
                filename="__init__.py",
            )
            should_skip = adapter.should_skip(ctx)
            assert should_skip, f"Should skip trivial __init__.py: {repr(content)}"
        
        # Test non-trivial __init__.py
        non_trivial = "from .module import something\npass"
        non_trivial_ctx = lctx(
            raw_text=non_trivial,
            filename="__init__.py",
        )
        should_not_skip = adapter.should_skip(non_trivial_ctx)
        assert not should_not_skip, "Should not skip non-trivial __init__.py"
    
    def test_error_handling(self, monkeypatch):
        """Test error handling when Tree-sitter has issues."""
        # Mock Tree-sitter to raise an error during parsing
        def mock_parse(self):
            raise RuntimeError("Mocked parsing error")
        
        monkeypatch.setattr("lg.adapters.python.adapter.PythonDocument._parse", mock_parse)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        # Should handle parsing errors gracefully
        with pytest.raises(Exception):
            adapter.process("def test(): pass", "py", group_size=1, mixed=False)
    
    def test_metadata_collection(self, python_code_sample):
        """Test that metadata is properly collected."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(python_code_sample, "py", group_size=1, mixed=False)
        
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
        if meta["code.removed.functions"] > 0 or meta["code.removed.methods"] > 0:
            # Some code was processed
            pass
