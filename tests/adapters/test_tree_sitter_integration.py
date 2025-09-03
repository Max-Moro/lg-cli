"""
Integration tests for Tree-sitter infrastructure.
Tests the complete pipeline from configuration to output.
"""

import pytest

from lg.adapters.python_tree_sitter import PythonTreeSitterAdapter
from lg.adapters.range_edits import RangeEditor, PlaceholderGenerator
from lg.adapters.tree_sitter_support import (
    is_tree_sitter_available, query_registry, get_supported_languages,
    create_document
)
from lg.adapters.typescript_tree_sitter import TypeScriptTreeSitterAdapter

pytestmark = pytest.mark.usefixtures("skip_if_no_tree_sitter")


class TestTreeSitterInfrastructure:
    """Test Tree-sitter infrastructure components."""
    
    def test_tree_sitter_availability(self):
        """Test Tree-sitter availability check."""
        assert is_tree_sitter_available() is True
    
    def test_supported_languages(self):
        """Test that expected languages are supported."""
        languages = get_supported_languages()
        expected = ["python", "typescript", "javascript"]  # Only installed modules
        
        for lang in expected:
            assert lang in languages, f"Language {lang} should be supported"
    
    def test_query_registry(self):
        """Test query registry functionality."""
        # Check that default queries are registered
        python_queries = query_registry.list_queries("python")
        assert "functions" in python_queries
        assert "methods" in python_queries
        assert "classes" in python_queries
        assert "imports" in python_queries
        
        typescript_queries = query_registry.list_queries("typescript")
        assert "functions" in typescript_queries
        assert "methods" in typescript_queries
        assert "interfaces" in typescript_queries
    
    def test_document_creation_and_parsing(self, python_code_sample):
        """Test document creation and basic parsing."""
        doc = create_document(python_code_sample, "python")
        
        assert doc.text == python_code_sample
        assert doc.lang_name == "python"
        assert doc.tree is not None
        assert doc.root_node is not None
    
    def test_query_execution(self, python_code_sample):
        """Test query execution on parsed document."""
        doc = create_document(python_code_sample, "python")
        
        # Test function query
        functions = doc.query("functions")
        assert len(functions) > 0
        
        # Check that we found functions (names are not captured in manual traversal yet)
        function_defs = [node for node, capture_name in functions if capture_name == "function_def"]
        assert len(function_defs) > 0, "Should find function definitions"
        
        # For now just check that we found some functions
        # TODO: Extract function names when proper query system is implemented
    
    def test_range_extraction(self, python_code_sample):
        """Test byte and line range extraction."""
        doc = create_document(python_code_sample, "python")
        
        functions = doc.query("functions")
        for node, capture_name in functions:
            if capture_name == "function_body":
                # Test byte range
                start_byte, end_byte = doc.get_node_range(node)
                assert start_byte < end_byte
                assert start_byte >= 0
                assert end_byte <= len(python_code_sample.encode('utf-8'))
                
                # Test line range
                start_line, end_line = doc.get_line_range(node)
                assert start_line <= end_line
                assert start_line >= 0
                
                # Test text extraction
                text = doc.get_node_text(node)
                assert len(text) > 0
                break


class TestRangeEditorSystem:
    """Test range-based editing system."""
    
    def test_basic_edit_operations(self):
        """Test basic edit operations."""
        text = "Hello, World!\nThis is a test."
        editor = RangeEditor(text)
        
        # Add some edits
        editor.add_replacement(0, 5, "Hi")  # "Hello" -> "Hi"
        editor.add_deletion(13, 14)  # Remove newline
        
        result, stats = editor.apply_edits()
        
        assert result == "Hi, World!This is a test."
        assert stats["edits_applied"] == 2
        assert stats["bytes_saved"] > 0
    
    def test_edit_validation(self):
        """Test edit validation."""
        text = "Short text"
        editor = RangeEditor(text)
        
        # Add invalid edit (out of bounds)
        editor.add_edit(0, 100, "replacement")
        
        errors = editor.validate_edits()
        assert len(errors) > 0
        assert "exceeds text length" in errors[0]
    
    def test_overlapping_edit_detection(self):
        """Test overlapping edit detection."""
        text = "1234567890"
        editor = RangeEditor(text)
        
        # Add overlapping edits
        editor.add_edit(2, 6, "AAA")  # positions 2-6
        editor.add_edit(4, 8, "BBB")  # positions 4-8 (overlaps)
        
        errors = editor.validate_edits()
        assert len(errors) > 0
        assert "Overlapping edits" in errors[0]
    
    def test_placeholder_generation(self):
        """Test placeholder generation for different languages."""
        # Test Python style
        python_style = PythonTreeSitterAdapter().get_comment_style()
        python_gen = PlaceholderGenerator(python_style)
        
        placeholder = python_gen.create_function_placeholder("test_func", 5, 100)
        assert placeholder.startswith("#")
        assert "5" in placeholder  # Line count
        
        # Test TypeScript style
        ts_style = TypeScriptTreeSitterAdapter().get_comment_style()
        ts_gen = PlaceholderGenerator(ts_style)
        
        placeholder = ts_gen.create_method_placeholder("testMethod", 3, 80, style="block")
        assert placeholder.startswith("/*")
        assert placeholder.endswith("*/")
        assert "3" in placeholder


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_python_adapter_full_pipeline(self, python_code_sample):
        """Test complete Python adapter pipeline."""
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = adapter.load_cfg({
            "strip_function_bodies": True,
            "placeholders": {
                "mode": "summary",
                "style": "inline"
            }
        })
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Verify processing occurred
        assert meta["edits_applied"] > 0
        assert meta["bytes_saved"] > 0
        assert meta["code.removed.functions"] > 0
        
        # Verify placeholders were inserted
        assert "# … " in result
        
        # Verify structure is preserved
        assert "class Calculator:" in result
        assert "def add(self, a: int, b: int) -> int:" in result
        
        # Verify docstrings are preserved
        assert '"""A simple calculator class."""' in result
    
    def test_typescript_adapter_full_pipeline(self, typescript_code_sample):
        """Test complete TypeScript adapter pipeline."""
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = adapter.load_cfg({
            "public_api_only": True,
            "strip_function_bodies": True,
            "placeholders": {
                "mode": "summary",
                "style": "block"
            }
        })
        
        result, meta = adapter.process(typescript_code_sample, group_size=1, mixed=False)
        
        # Verify processing occurred
        assert meta["_adapter"] == "typescript"
        
        # Verify placeholders were inserted in block style
        assert "/* … " in result and " */" in result
        
        # Verify TypeScript structure is preserved
        assert "interface User {" in result
        assert "class UserService {" in result
    
    def test_error_handling_and_fallback(self, python_code_sample, monkeypatch):
        """Test error handling and fallback behavior."""
        # Test with Tree-sitter unavailable
        monkeypatch.setattr("lg.adapters.code_base.is_tree_sitter_available", lambda: False)
        
        adapter = PythonTreeSitterAdapter()
        adapter._cfg = adapter.load_cfg({"strip_function_bodies": True})
        
        result, meta = adapter.process(python_code_sample, group_size=1, mixed=False)
        
        # Should fall back gracefully
        assert meta["_fallback_mode"] is True
        assert result == python_code_sample  # Unchanged
        assert meta["code.removed.functions"] == 0
    
    def test_configuration_loading(self):
        """Test configuration loading from various formats."""
        # Test simple boolean config
        adapter = PythonTreeSitterAdapter()
        cfg = adapter.load_cfg({"strip_function_bodies": True})
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
        
        cfg = adapter.load_cfg(complex_config)
        assert hasattr(cfg.strip_function_bodies, 'mode')
        assert cfg.strip_function_bodies.mode == "large_only"
        assert cfg.strip_function_bodies.min_lines == 10
