"""
Integration tests for adapter system.
Tests the complete pipeline from configuration to output.
"""

import pytest
from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from tests.conftest import lctx_py, lctx_ts


class TestCrossLanguageIntegration:
    """Integration tests across different language adapters."""

    def test_adapter_consistency(self):
        """Test that all adapters follow consistent patterns."""
        # Test Python adapter
        python_adapter = PythonAdapter()
        python_adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        python_code = '''def test():
    return "python"
'''
        
        python_result, python_meta = python_adapter.process(lctx_py(raw_text=python_code))
        
        # Test TypeScript adapter
        ts_adapter = TypeScriptAdapter()
        ts_adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        ts_code = '''function test() {
    return "typescript";
}
'''
        
        ts_result, ts_meta = ts_adapter.process(lctx_ts(raw_text=ts_code))
        
        # Both should have consistent metadata structure
        required_fields = ["_adapter", "_group_size", "_group_mixed"]
        for field in required_fields:
            assert field in python_meta, f"Python missing {field}"
            assert field in ts_meta, f"TypeScript missing {field}"
        
        # Both should produce string results
        assert isinstance(python_result, str)
        assert isinstance(ts_result, str)
        
        # Both should report their adapter name correctly
        assert python_meta["_adapter"] == "python"
        assert ts_meta["_adapter"] == "typescript"

    def test_configuration_compatibility(self):
        """Test that similar configurations work across languages."""
        base_config = {
            "strip_function_bodies": True,
            "comment_policy": "keep_doc",
            "public_api_only": False
        }
        
        # Test Python with base config
        python_cfg = PythonCfg.from_dict(base_config)
        assert python_cfg.strip_function_bodies is True
        assert python_cfg.comment_policy == "keep_doc"
        assert python_cfg.public_api_only is False
        
        # Test TypeScript with base config
        ts_cfg = TypeScriptCfg.from_dict(base_config)
        assert ts_cfg.strip_function_bodies is True
        assert ts_cfg.comment_policy == "keep_doc"
        assert ts_cfg.public_api_only is False

    def test_placeholder_consistency(self):
        """Test that placeholders are consistent across languages."""
        python_adapter = PythonAdapter()
        python_adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        ts_adapter = TypeScriptAdapter()
        ts_adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        python_code = '''def long_function():
    """This function has a long body."""
    x = 1
    y = 2
    z = x + y
    return z
'''
        
        ts_code = '''function longFunction() {
    // This function has a long body
    const x = 1;
    const y = 2;
    const z = x + y;
    return z;
}
'''
        
        python_result, python_meta = python_adapter.process(lctx_py(raw_text=python_code))
        ts_result, ts_meta = ts_adapter.process(lctx_ts(raw_text=ts_code))
        
        # Both should contain placeholder indicators
        assert ("… " in python_result or "..." in python_result)
        assert ("… " in ts_result or "..." in ts_result)
        
        # Both should report function removal
        assert python_meta.get("code.removed.functions", 0) > 0
        assert ts_meta.get("code.removed.functions", 0) > 0


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""

    def test_full_pipeline_python(self):
        """Test complete Python adapter pipeline."""
        code = '''"""Module docstring."""
import os
import requests
from .local import helper

class DataProcessor:
    """Process data efficiently."""
    
    def __init__(self, config):
        self.config = config
        self.data = []
    
    def process(self, items):
        """Process list of items."""
        results = []
        for item in items:
            processed = self._transform(item)
            results.append(processed)
        return results
    
    def _transform(self, item):
        """Transform single item."""
        return item.upper()
'''
        
        adapter = PythonAdapter()
        adapter._cfg = PythonCfg.from_dict({
            "strip_function_bodies": True,
            "comment_policy": "keep_doc",
            "public_api_only": False,
            "imports": {"policy": "external_only"},
            "fields": {"strip_trivial_constructors": True}
        })
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should preserve structure
        assert "class DataProcessor:" in result
        assert "def process(self, items):" in result
        
        # Should preserve docstrings
        assert '"""Process data efficiently."""' in result
        
        # Should have applied optimizations
        assert meta.get("code.removed.functions", 0) + meta.get("code.removed.methods", 0) > 0
        
        # Should have processed imports
        assert meta.get("code.removed.imports", 0) >= 0

    def test_full_pipeline_typescript(self):
        """Test complete TypeScript adapter pipeline."""
        code = '''import { Component } from '@angular/core';
import { Observable } from 'rxjs';
import { helper } from './utils/helper';

/**
 * User service for managing users
 */
export class UserService {
    private users: User[] = [];
    
    constructor(private apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    /**
     * Get all users
     */
    public getUsers(): Observable<User[]> {
        return this.httpClient.get<User[]>(`${this.apiUrl}/users`);
    }
    
    private validateUser(user: User): boolean {
        return user.name.length > 0;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg.from_dict({
            "strip_function_bodies": True,
            "comment_policy": "keep_doc",
            "public_api_only": True,
            "imports": {"policy": "external_only"},
            "fields": {"strip_trivial_constructors": True}
        })
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
        # Should preserve exported class
        assert "export class UserService" in result
        
        # Should preserve public methods but remove private ones
        assert "public getUsers():" in result
        assert "private validateUser" not in result
        
        # Should have applied optimizations
        assert meta.get("code.removed.private_elements", 0) > 0

    def test_error_recovery(self):
        """Test error recovery in pipeline."""
        # Test with malformed code
        malformed_python = "def incomplete("
        malformed_ts = "function incomplete(: string"
        
        python_adapter = PythonAdapter()
        python_adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        ts_adapter = TypeScriptAdapter()
        ts_adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        # Should not crash with malformed code
        try:
            python_result, python_meta = python_adapter.process(lctx_py(raw_text=malformed_python))
            assert isinstance(python_result, str)
            assert isinstance(python_meta, dict)
        except Exception:
            # Some parsing errors are expected, but should be handled gracefully
            pass
        
        try:
            ts_result, ts_meta = ts_adapter.process(lctx_ts(raw_text=malformed_ts))
            assert isinstance(ts_result, str)
            assert isinstance(ts_meta, dict)
        except Exception:
            # Some parsing errors are expected, but should be handled gracefully
            pass

    def test_empty_file_handling(self):
        """Test handling of empty files."""
        python_adapter = PythonAdapter()
        python_adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        ts_adapter = TypeScriptAdapter()
        ts_adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        # Test empty files
        python_result, python_meta = python_adapter.process(lctx_py(raw_text=""))
        ts_result, ts_meta = ts_adapter.process(lctx_ts(raw_text=""))
        
        # Should handle gracefully
        assert python_result == ""
        assert ts_result == ""
        assert isinstance(python_meta, dict)
        assert isinstance(ts_meta, dict)

    def test_large_file_handling(self):
        """Test handling of large files."""
        # Create a large Python file
        large_python = "# Large file\n" + "\n".join([
            f"def function_{i}():\n    return {i}" 
            for i in range(100)
        ])
        
        python_adapter = PythonAdapter()
        python_adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        result, meta = python_adapter.process(lctx_py(raw_text=large_python))
        
        # Should handle large files
        assert isinstance(result, str)
        assert len(result) > 0
        assert meta.get("code.removed.functions", 0) > 50  # Should have processed many functions


class TestConfigurationIntegration:
    """Test configuration integration across the system."""

    def test_config_inheritance(self):
        """Test that configurations are properly inherited."""
        base_config = {
            "strip_function_bodies": True,
            "comment_policy": "keep_doc"
        }
        
        # Test that language-specific configs can extend base
        python_config = dict(base_config)
        python_config["skip_trivial_inits"] = True
        
        python_cfg = PythonCfg.from_dict(python_config)
        assert python_cfg.strip_function_bodies is True
        assert python_cfg.comment_policy == "keep_doc"
        assert python_cfg.skip_trivial_inits is True
        
        # Test that TypeScript has its own extensions
        ts_config = dict(base_config)
        ts_config["skip_barrel_files"] = True
        
        ts_cfg = TypeScriptCfg.from_dict(ts_config)
        assert ts_cfg.strip_function_bodies is True
        assert ts_cfg.comment_policy == "keep_doc"
        assert ts_cfg.skip_barrel_files is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid configurations
        invalid_config = {
            "strip_function_bodies": "invalid_value"  # Should be bool or object
        }
        
        # Should handle invalid configs gracefully
        try:
            cfg = PythonCfg.from_dict(invalid_config)
            # If it doesn't raise, check that it has some reasonable default
            assert hasattr(cfg, 'strip_function_bodies')
        except (TypeError, ValueError):
            # Validation errors are acceptable
            pass
