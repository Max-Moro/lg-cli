from lg.adapters.python import PythonAdapter
from lg.adapters.range_edits import RangeEditor, PlaceholderGenerator
from lg.adapters.typescript import TypeScriptAdapter


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
        python_style = PythonAdapter().get_comment_style()
        python_gen = PlaceholderGenerator(python_style)
        
        placeholder = python_gen.create_function_placeholder( 5, 100)
        assert placeholder.startswith("#")
        assert "5" in placeholder  # Line count
        
        # Test TypeScript style
        ts_style = TypeScriptAdapter().get_comment_style()
        ts_gen = PlaceholderGenerator(ts_style)
        
        placeholder = ts_gen.create_method_placeholder( 3, 80, style="block")
        assert placeholder.startswith("/*")
        assert placeholder.endswith("*/")
        assert "3" in placeholder
