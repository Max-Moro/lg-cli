"""
Smoke tests that work even without Tree-sitter dependencies.
Tests fallback behavior and basic adapter loading.
"""

import pytest
from unittest.mock import patch

from lg.adapters.python_tree_sitter import PythonTreeSitterAdapter
from lg.adapters.typescript_tree_sitter import TypeScriptTreeSitterAdapter
from lg.adapters.code_model import PythonCfg, TypeScriptCfg


class TestSmokeWithoutDeps:
    """Test basic functionality without Tree-sitter dependencies."""
    
    def test_adapter_loading_without_tree_sitter(self):
        """Test that adapters can be loaded even without Tree-sitter."""
        # This should work even if tree-sitter is not installed
        python_adapter = PythonTreeSitterAdapter()
        ts_adapter = TypeScriptTreeSitterAdapter()
        
        assert python_adapter.name == "python"
        assert ts_adapter.name == "typescript"
        assert ".py" in python_adapter.extensions
        assert ".ts" in ts_adapter.extensions
    
    def test_config_loading_without_tree_sitter(self):
        """Test configuration loading without Tree-sitter."""
        python_adapter = PythonTreeSitterAdapter()
        
        # Basic config loading should work
        cfg = python_adapter.load_cfg({"strip_function_bodies": True})
        assert isinstance(cfg, PythonCfg)
        assert cfg.strip_function_bodies is True
    
    @patch('lg.adapters.code_base.is_tree_sitter_available', return_value=False)
    def test_fallback_processing(self, mock_available):
        """Test fallback processing when Tree-sitter is not available."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = PythonCfg(strip_function_bodies=True)
        
        test_code = '''
def test_function():
    return "hello world"
'''
        
        result, meta = adapter.process(test_code, group_size=1, mixed=False)
        
        # Should fall back gracefully
        assert meta["_fallback_mode"] is True
        assert result == test_code  # Original unchanged
        assert meta["code.removed.functions"] == 0
        assert meta["_adapter"] == "python"
    
    def test_should_skip_functionality(self, tmp_path):
        """Test should_skip functionality without Tree-sitter."""
        adapter = PythonTreeSitterAdapter()
        
        # Test __init__.py skipping logic
        init_file = tmp_path / "__init__.py"
        
        # Trivial __init__.py should be skipped
        trivial_content = "pass"
        should_skip = adapter.should_skip(init_file, trivial_content)
        assert should_skip is True
        
        # Non-trivial __init__.py should not be skipped
        real_content = "from .module import something"
        should_not_skip = adapter.should_skip(init_file, real_content)
        assert should_not_skip is False
    
    def test_import_structure(self):
        """Test that imports work correctly."""
        # Test that we can import the modules
        from lg.adapters import tree_sitter_support
        from lg.adapters import range_edits
        from lg.adapters import code_base
        
        # Even if Tree-sitter is not available, the modules should load
        assert hasattr(tree_sitter_support, 'is_tree_sitter_available')
        assert hasattr(range_edits, 'RangeEditor')
        assert hasattr(code_base, 'CodeAdapter')
    
    def test_range_editor_basic_functionality(self):
        """Test range editor without Tree-sitter."""
        from lg.adapters.range_edits import RangeEditor
        
        text = "Hello, World!"
        editor = RangeEditor(text)
        
        # Test basic operations
        editor.add_replacement(0, 5, "Hi")  # "Hello" -> "Hi"
        
        result, stats = editor.apply_edits()
        assert result == "Hi, World!"
        assert stats["edits_applied"] == 1
        assert stats["bytes_saved"] > 0
    
    def test_placeholder_generation(self):
        """Test placeholder generation without Tree-sitter."""
        from lg.adapters.range_edits import PlaceholderGenerator, get_comment_style
        
        # Test comment style detection
        python_style = get_comment_style("python")
        assert python_style[0] == "#"
        
        ts_style = get_comment_style("typescript")
        assert ts_style[0] == "//"
        
        # Test placeholder generation
        gen = PlaceholderGenerator(python_style)
        placeholder = gen.create_function_placeholder("test", 5, 100)
        assert "#" in placeholder
        assert "5" in placeholder
