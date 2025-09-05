"""
Tests for based Python adapter.
"""

import pytest
from lg.adapters.code_model import FunctionBodyConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from .conftest import assert_golden_match, lctx, lctx_py


class TestPythonAdapter:
    """Test suite for Python adapter."""
    
    def test_basic_function_stripping(self, python_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        # Create lightweight context with sample code
        ctx = lctx_py(raw_text=python_code_sample)
        
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
        
        result, meta = adapter.process(lctx_py(raw_text=python_code_sample))
        
        # Should have fewer removals than basic test
        golden_file = tmp_path / "python_large_only_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_no_stripping(self, python_code_sample):
        """Test with stripping disabled."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(lctx_py(raw_text=python_code_sample))
        
        # No functions should be removed
        assert meta.get("code.removed.functions", 0) == 0
        assert meta.get("code.removed.methods", 0) == 0
        # Result should be close to original (may have minor whitespace changes)
        assert "def add(self, a: int, b: int) -> int:" in result
        assert "result = a + b" in result

    def test_trivial_init_py_skipping(self, tmp_path):
        """Test that trivial __init__.py files are skipped."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg()

        # Тривиальные случаи (__init__.py): пусто, pass, ..., комментарии + pass/...
        trivial_cases = [
            "",
            "pass",
            "...",
            "# Comment\npass",
            "# Comment\n...",
        ]

        for i, content in enumerate(trivial_cases):
            ctx = lctx(
                raw_text=content,
                filename="__init__.py",
            )
            should_skip = adapter.should_skip(ctx)
            assert should_skip, f"Should skip trivial __init__.py: {repr(content)}"

        # Только комментарии — НЕ тривиальный
        comment_only_ctx = lctx(
            raw_text="# Comment only",
            filename="__init__.py",
        )
        assert not adapter.should_skip(comment_only_ctx), "Comment-only __init__.py must NOT be considered trivial"

        # Редекларация публичного API (только относительные импорты / __all__) — тривиальный
        reexport_ctx = lctx(
            raw_text="from .module import something\n__all__ = ['something']",
            filename="__init__.py",
        )
        assert adapter.should_skip(reexport_ctx), "Re-export-only __init__.py should be considered trivial"

        # Нетривиальный: есть «настоящее» содержимое
        non_trivial = "from .module import something\nvalue = 42"
        non_trivial_ctx = lctx(
            raw_text=non_trivial,
            filename="__init__.py",
        )
        should_not_skip = adapter.should_skip(non_trivial_ctx)
        assert not should_not_skip, "Should not skip non-trivial __init__.py"
    
    def test_error_handling(self, monkeypatch):
        """Test error handling when Tree-sitter has issues."""
        # Mock Tree-sitter to raise an error during parsing
        def mock_parse():
            raise RuntimeError("Mocked parsing error")
        
        monkeypatch.setattr("lg.adapters.python.adapter.PythonDocument._parse", mock_parse)
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        # Should handle parsing errors gracefully
        with pytest.raises(Exception):
            adapter.process(lctx_py(raw_text="def test(): pass"))
    
    def test_metadata_collection(self, python_code_sample):
        """Test that metadata is properly collected."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(lctx_py(raw_text=python_code_sample))
        
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
