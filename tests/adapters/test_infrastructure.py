"""
Tests for adapter infrastructure components.
"""

from lg.adapters.range_edits import RangeEditor
from lg.adapters.registry import get_adapter_for_path
from pathlib import Path


class TestRangeEditorSystem:
    """Test range-based editing system."""
    
    def test_basic_edit_operations(self):
        """Test basic edit operations."""
        text = "Hello, World!\nThis is a test."
        editor = RangeEditor(text)
        
        # Add some edits
        editor.add_replacement(0, 5, "Hi", None)  # "Hello" -> "Hi"
        editor.add_deletion(13, 14, None)  # Remove newline
        
        result, stats = editor.apply_edits()
        
        assert result == "Hi, World!This is a test."
        assert stats["edits_applied"] == 2
        assert stats["bytes_saved"] > 0
    
    def test_edit_validation(self):
        """Test edit validation."""
        text = "Short text"
        editor = RangeEditor(text)
        
        # Add invalid edit (out of bounds)
        editor.add_edit(0, 100, "replacement", None)
        
        errors = editor.validate_edits()
        assert len(errors) > 0
        assert "exceeds text length" in errors[0]

    def test_overlapping_edit_handling(self):
        """Test that overlapping edits are handled correctly (first-wins policy)."""
        text = "Hello, World! This is a test."
        editor = RangeEditor(text)
        
        # Add overlapping edits - first should win
        editor.add_replacement(0, 5, "Hi", None)     # "Hello" -> "Hi"
        editor.add_replacement(2, 7, "Bye", None)    # Overlaps with first edit
        
        result, stats = editor.apply_edits()
        
        # Only first edit should be applied
        assert result == "Hi, World! This is a test."
        assert stats["edits_applied"] == 1


class TestAdapterRegistry:
    """Test adapter registry system."""
    
    def test_adapter_resolution_by_extension(self):
        """Test that correct adapters are resolved by file extension."""
        # Test Python files
        python_path = Path("test.py")
        python_adapter_cls = get_adapter_for_path(python_path)
        assert python_adapter_cls.name == "python"
        
        # Test TypeScript files
        ts_path = Path("test.ts")
        ts_adapter_cls = get_adapter_for_path(ts_path)
        assert ts_adapter_cls.name == "typescript"
        
        tsx_path = Path("test.tsx")
        tsx_adapter_cls = get_adapter_for_path(tsx_path)
        assert tsx_adapter_cls.name == "typescript"
        
        # Test Markdown files
        md_path = Path("test.md")
        md_adapter_cls = get_adapter_for_path(md_path)
        assert md_adapter_cls.name == "markdown"
    
    def test_unknown_extension_fallback(self):
        """Test fallback to base adapter for unknown extensions."""
        unknown_path = Path("test.unknown")
        adapter_cls = get_adapter_for_path(unknown_path)
        assert adapter_cls.name == "base"
    
    def test_case_insensitive_extension_matching(self):
        """Test that extension matching is case-insensitive."""
        upper_py_path = Path("test.PY")
        adapter_cls = get_adapter_for_path(upper_py_path)
        assert adapter_cls.name == "python"
        
        upper_ts_path = Path("test.TS")
        adapter_cls = get_adapter_for_path(upper_ts_path)
        assert adapter_cls.name == "typescript"


class TestAdapterMetrics:
    """Test adapter metrics collection."""
    
    def test_metrics_collection_basic(self):
        """Test basic metrics collection."""
        from lg.adapters.metrics import MetricsCollector
        
        collector = MetricsCollector("test")
        
        # Test ленивый инкремент
        collector.increment("test.counter")
        collector.increment("test.counter", 2)
        
        assert collector.get("test.counter") == 3
        
        # Test установка значений
        collector.set("test.value", "hello")
        assert collector.get("test.value") == "hello"
    
    def test_metrics_merge(self):
        """Test merging of metrics collectors."""
        from lg.adapters.metrics import MetricsCollector
        
        collector1 = MetricsCollector("python")
        collector1.increment("functions", 2)

        collector2 = MetricsCollector("python")
        collector2.increment("functions", 3)
        collector2.increment("methods", 1)
        
        collector1.merge(collector2)
        
        assert collector1.get("functions") == 5  # 2 + 3
        assert collector1.get("methods") == 1


class TestTreeSitterInfrastructure:
    """Test Tree-sitter infrastructure components."""
    
    def test_document_creation(self, skip_if_no_tree_sitter):
        """Test Tree-sitter document creation."""
        from lg.adapters.python.adapter import PythonDocument
        
        code = '''def hello():
    """Say hello."""
    return "hello"
'''
        
        doc = PythonDocument(code, "py")
        
        # Test basic functionality
        assert doc.text == code
        assert doc.ext == "py"
        assert doc.tree is not None
        assert not doc.has_error()
    
    def test_query_execution(self, skip_if_no_tree_sitter):
        """Test query execution on Tree-sitter documents."""
        from lg.adapters.python.adapter import PythonDocument
        
        code = '''def hello():
    """Say hello."""
    return "hello"

class Greeter:
    def greet(self):
        return "greetings"
'''
        
        doc = PythonDocument(code, "py")
        
        # Test function query
        functions = doc.query("functions")
        assert len(functions) > 0
        
        # Test comment query
        comments = doc.query("comments")
        assert len(comments) > 0
        
        # Should find docstring
        found_docstring = any(capture_name == "docstring" for node, capture_name in comments)
        assert found_docstring
    
    def test_node_text_extraction(self, skip_if_no_tree_sitter):
        """Test extracting text from Tree-sitter nodes."""
        from lg.adapters.python.adapter import PythonDocument
        
        code = '''def hello():
    return "hello"
'''
        
        doc = PythonDocument(code, "py")
        functions = doc.query("functions")
        
        # Should be able to extract function name
        for node, capture_name in functions:
            if capture_name == "function_name":
                function_name = doc.get_node_text(node)
                assert function_name == "hello"
                break
