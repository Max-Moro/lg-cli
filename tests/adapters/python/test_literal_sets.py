"""
Tests for Python set literal trimming optimization.
Ensures set literals are correctly identified and trimmed with proper bracket types.
"""

from lg.adapters.code_model import LiteralConfig
from lg.adapters.python import PythonCfg
from tests.adapters.python.conftest import make_adapter
from tests.conftest import lctx_py


class TestPythonSetLiterals:
    """Test set literal handling in Python adapter."""

    def test_set_literal_structure_identification(self):
        """Test that set literals are correctly identified with proper boundaries."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=10))
        adapter = make_adapter(cfg)
        
        # Create a set literal that exceeds token limit
        code = '''
TAGS = {
    "python", "javascript", "typescript", "java", "csharp", "cpp", "rust",
    "go", "kotlin", "swift", "php", "ruby", "scala", "clojure", "haskell"
}
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Verify set boundaries are preserved
        assert "TAGS = {" in result
        assert result.count("{") == result.count("}")
        
        # Verify it's identified as a set, not array
        assert "literal set" in result
        assert "literal array" not in result
        
        # Verify no incorrect bracket types
        assert "TAGS = [" not in result
        assert "] #" not in result

    def test_set_vs_dict_distinction(self):
        """Test that sets and dicts are correctly distinguished."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=10))
        adapter = make_adapter(cfg)
        
        # Set literal (no colons)
        set_code = '''
TAGS = {
    "python", "javascript", "typescript", "java", "csharp"
}
'''
        
        # Dict literal (has colons)
        dict_code = '''
CONFIG = {
    "language": "python", 
    "version": "3.9", 
    "features": "all"
}
'''
        
        set_result, _ = adapter.process(lctx_py(set_code.strip()))
        dict_result, _ = adapter.process(lctx_py(dict_code.strip()))
        
        # Set should be identified as set
        assert "literal set" in set_result
        assert "TAGS = {" in set_result
        
        # Dict should be identified as object
        assert "literal object" in dict_result
        assert "CONFIG = {" in dict_result

    def test_empty_set_handling(self):
        """Test handling of empty sets."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=1))  # Very low limit
        adapter = make_adapter(cfg)
        
        code = '''
EMPTY_SET = set()
EMPTY_LITERAL_SET = {}  # This is actually an empty dict in Python
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Empty dict literal should remain unchanged or be handled as object
        # set() constructor call is not a literal, so should be unchanged
        assert "EMPTY_SET = set()" in result
        
    def test_multiline_set_formatting(self):
        """Test that multiline sets maintain proper indentation."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=10))
        adapter = make_adapter(cfg)
        
        code = '''
class Config:
    SUPPORTED_LANGS = {
        "python", "javascript", "typescript", 
        "java", "csharp", "cpp", "rust",
        "go", "kotlin", "swift"
    }
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Check that set boundaries are correct
        assert "SUPPORTED_LANGS = {" in result
        assert result.count("{") == result.count("}")
        
        # Check indentation is preserved
        lines = result.split('\n')
        set_lines = [line for line in lines if 'SUPPORTED_LANGS' in line or (line.strip() and '"' in line)]
        if len(set_lines) > 1:
            # Multiline - check indentation consistency
            indent_levels = [len(line) - len(line.lstrip()) for line in set_lines[1:] if line.strip()]
            if indent_levels:
                assert all(indent == indent_levels[0] for indent in indent_levels), "Inconsistent indentation"

    def test_set_fallback_from_wrong_capture(self):
        """Test that sets are correctly handled even if Tree-sitter gives wrong capture_name."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=10))
        adapter = make_adapter(cfg)
        
        # This tests the fallback logic in _analyze_literal_structure
        # when capture_name is "array" but the literal is actually a set
        code = '''
# This should be detected as set despite potentially wrong capture
LANGUAGES = {
    "python", "java", "javascript", "typescript", "csharp"
}
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Should correctly identify as set and use {} brackets
        assert "LANGUAGES = {" in result
        assert "literal set" in result
        assert "LANGUAGES = [" not in result

    def test_set_with_complex_elements(self):
        """Test sets with complex string elements."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=15))
        adapter = make_adapter(cfg)
        
        code = '''
COMPLEX_SET = {
    "element_with_underscores", 
    "element-with-hyphens",
    "element.with.dots",
    "element with spaces",
    "element,with,commas"
}
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Should preserve set boundaries
        assert "COMPLEX_SET = {" in result
        assert result.count("{") == result.count("}")
        assert "literal set" in result

    def test_set_metrics(self):
        """Test that metrics are correctly recorded for set literals."""
        cfg = PythonCfg(literals=LiteralConfig(max_tokens=5))
        adapter = make_adapter(cfg)
        
        code = '''
BIG_SET = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"
}
'''
        
        lctx = lctx_py(code.strip())
        result, meta = adapter.process(lctx)
        
        # Check that literal removal is recorded in metrics
        assert meta.get("python.removed.literal", 0) >= 1
        assert "literal set" in result
