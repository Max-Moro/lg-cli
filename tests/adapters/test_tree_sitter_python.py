"""
Tests for Tree-sitter based Python adapter.
"""

import pytest
from pathlib import Path

from lg.adapters.python_tree_sitter import PythonTreeSitterAdapter, PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from tests.adapters.conftest import assert_golden_match, create_temp_file


pytestmark = pytest.mark.usefixtures("skip_if_no_tree_sitter")


class TestPythonTreeSitterAdapter:
    """Test suite for Python Tree-sitter adapter."""
    
    def test_basic_function_stripping(self, python_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Check that functions were processed
        assert meta["code.removed.functions"] > 0
        assert meta["code.removed.methods"] > 0
        assert "# … function body omitted" in result or "# … method body omitted" in result
        
        # Golden file test
        golden_file = tmp_path / "python_basic_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_large_only_function_stripping(self, python_code_sample, tmp_path):
        """Test stripping only large functions."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=3
            )
        )
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Should have fewer removals than basic test
        golden_file = tmp_path / "python_large_only_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_no_stripping(self, python_code_sample):
        """Test with stripping disabled."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # No functions should be removed
        assert meta["code.removed.functions"] == 0
        assert meta["code.removed.methods"] == 0
        # Result should be close to original (may have minor whitespace changes)
        assert "def add(self, a: int, b: int) -> int:" in result
        assert "result = a + b" in result
    
    def test_trivial_init_py_skipping(self, tmp_path):
        """Test that trivial __init__.py files are skipped."""
        adapter = PythonTreeSitterAdapter()
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
            # Все файлы должны называться __init__.py чтобы логика сработала
            subdir = tmp_path / f"subdir_{i}"
            subdir.mkdir(exist_ok=True)
            init_file = create_temp_file(subdir, "__init__.py", content)
            should_skip = adapter.should_skip(init_file, content)
            assert should_skip, f"Should skip trivial __init__.py: {repr(content)}"
        
        # Test non-trivial __init__.py
        non_trivial = "from .module import something\npass"
        real_package = tmp_path / "real_package"
        real_package.mkdir(exist_ok=True)
        non_trivial_file = create_temp_file(real_package, "__init__.py", non_trivial)
        should_not_skip = adapter.should_skip(non_trivial_file, non_trivial)
        assert not should_not_skip, "Should not skip non-trivial __init__.py"
    
    def test_fallback_mode(self, python_code_sample, monkeypatch):
        """Test fallback mode when Tree-sitter is not available."""
        # Mock Tree-sitter as unavailable
        monkeypatch.setattr("lg.adapters.code_base.is_tree_sitter_available", lambda: False)
        
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Should use fallback mode
        assert meta["_fallback_mode"] is True
        assert meta["code.removed.functions"] == 0  # No processing in fallback
        assert result == python_code_sample  # Original text unchanged
    
    def test_metadata_collection(self, python_code_sample):
        """Test that metadata is properly collected."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Check required metadata fields
        required_fields = [
            "_group_size", "_group_mixed", "_adapter",
            "code.removed.functions", "code.removed.methods",
            "edits_applied", "bytes_removed", "bytes_added", "bytes_saved"
        ]
        
        for field in required_fields:
            assert field in meta, f"Missing metadata field: {field}"
        
        assert meta["_adapter"] == "python"
        assert meta["_group_size"] == 1
        assert meta["_group_mixed"] is False
        
        # Should have some edits applied
        if meta["edits_applied"] > 0:
            assert meta["bytes_saved"] > 0  # Should save bytes by removing code
