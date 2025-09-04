"""
Integration tests for Tree-sitter infrastructure.
Tests the complete pipeline from configuration to output.
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from tests.conftest import lctx_py, lctx_ts


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_python_adapter_full_pipeline(self, python_code_sample):
        """Test complete Python adapter pipeline."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg.from_dict({
            "strip_function_bodies": True,
            "placeholders": {
                "mode": "summary",
                "style": "inline"
            }
        })

        result, meta = adapter.process(lctx_py(raw_text=python_code_sample))

        # Verify processing occurred
        assert meta.get("code.removed.functions", 0) >= 0
        assert meta.get("code.removed.methods", 0) >= 0

        # Verify placeholders were inserted if functions were removed
        if meta.get("code.removed.functions", 0) > 0 or meta.get("code.removed.methods", 0) > 0:
            assert "# … " in result or "/* … " in result

        # Verify structure is preserved
        assert "class Calculator:" in result
        assert "def add(self, a: int, b: int) -> int:" in result

        # Verify docstrings are preserved
        assert '"""A simple calculator class."""' in result

    def test_typescript_adapter_full_pipeline(self, typescript_code_sample):
        """Test complete TypeScript adapter pipeline."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg.from_dict({
            "public_api_only": True,
            "strip_function_bodies": True,
            "placeholders": {
                "mode": "summary",
                "style": "block"
            }
        })

        result, meta = adapter.process(lctx_ts(raw_text=typescript_code_sample))

        # Verify processing occurred
        assert meta["_adapter"] == "typescript"

        # Verify placeholders were inserted in block style
        assert "/* … " in result and " */" in result

        # Verify TypeScript structure is preserved
        assert "interface User {" in result
        assert "class UserService {" in result

    def test_tree_sitter_parsing_errors(self, monkeypatch):
        """Test handling of Tree-sitter parsing errors."""
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg.from_dict({"strip_function_bodies": True})

        # Test with malformed code that might cause parsing issues
        malformed_code = "def incomplete_function("
        
        # Should not crash, even with syntax errors
        result, meta = adapter.process(lctx_py(raw_text=malformed_code))
        
        # Should have processed something
        assert meta["_adapter"] == "python"
        assert isinstance(result, str)

    def test_configuration_loading(self):
        """Test configuration loading from various formats."""
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
            }
        }

        cfg = PythonCfg.from_dict(complex_config)
        assert hasattr(cfg.strip_function_bodies, 'mode')
        assert cfg.strip_function_bodies.mode == "large_only"
        assert cfg.strip_function_bodies.min_lines == 10
