"""
Test smart comment placement for literal optimization in Kotlin.
Ensures comments don't break code structure when placed inline.
"""

from lg.adapters.kotlin import KotlinCfg
from .conftest import make_adapter


class TestLiteralCommentContext:
    """Test smart comment placement for literal optimization."""
    
    def test_literal_at_end_of_line(self):
        """Test literal at end of line - should use single-line comment."""
        code = '''val message = "this is a very long message that should be trimmed because it exceeds token limits"'''
        
        cfg = KotlinCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use single-line comment since nothing follows on same line
        assert '//' in result
        assert 'literal string' in result
        assert '/*' not in result  # Should not use block comment
    
    def test_literal_with_code_after(self):
        """Test literal with other code after it - should use block comment."""
        code = 'val msg = "very long message that needs trimming"; println(msg)'
        
        cfg = KotlinCfg()
        cfg.literals.max_tokens = 5  # Force trimming  
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment to avoid commenting out the println statement
        assert '/*' in result and 'literal string' in result
        assert '*/ println(msg)' in result or '/* literal string' in result
    
    def test_literal_in_function_call(self):
        """Test literal inside function call - should use block comment."""
        code = 'println("this is a very long message that should be trimmed", otherParam)'
        
        cfg = KotlinCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since function call continues
        assert '/*' in result and 'literal string' in result
    
    def test_literal_in_data_class(self):
        """Test literal in data class initialization."""
        code = '''data class Config(
    val timeout: Long = 5000,
    val message: String = "this is a very long default message that should be trimmed"
)'''
        
        cfg = KotlinCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use appropriate comment style
        assert '//' in result or '/*' in result
        assert 'literal string' in result
    
    def _make_context(self, code: str):
        """Helper to create LightweightContext for testing."""
        from tests.infrastructure import lctx_kt
        return lctx_kt(code)

