"""
Test smart comment placement for literal optimization in TypeScript.
Ensures comments don't break code structure when placed inline.
"""

from lg.adapters.typescript import TypeScriptCfg
from .utils import make_adapter


class TestLiteralCommentContext:
    """Test smart comment placement for literal optimization."""
    
    def test_literal_with_semicolon_immediate(self):
        """Test literal with semicolon immediately after - should use single-line comment after semicolon."""
        code = 'const message = "very long string that should be trimmed for optimization purposes and exceed the token limit";'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place single-line comment after semicolon
        assert '; //' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment
    
    def test_literal_with_code_after(self):
        """Test literal with other code after it - should place comment after semicolon with block comment."""
        code = 'function getLastLogin(): string { date = "2024-01-15T10:30:00Z"; return date; }'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place comment after semicolon with block comment to avoid commenting out the return statement
        assert '"; /* literal string' in result
        assert '*/ return date' in result
        assert '//' not in result  # Should not use single-line comment
    
    def test_literal_at_end_of_line(self):
        """Test literal at end of line - should use single-line comment."""
        code = '''const message = "this is a very long message that should be trimmed because it exceeds token limits"'''
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use single-line comment since nothing follows on same line
        assert '//' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment
    
    def test_literal_with_closing_brace(self):
        """Test literal followed by closing brace - should use block comment since there's code after semicolon."""
        code = 'function getDate(): string { return "2024-01-15T10:30:00Z very long timestamp"; }'
        
        cfg = TypeScriptCfg()  
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since there's code (closing brace) after semicolon
        assert '/* literal string' in result
        assert '*/ }' in result
        assert '//' not in result  # Should not use single-line comment
    
    def test_literal_with_semicolon_and_more_code(self):
        """Test literal with semicolon followed by more code - should place comment after semicolon with block comment."""
        code = 'const msg = "this is a very long message that should be trimmed"; console.log(msg);'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place comment after semicolon with block comment to avoid commenting out following code
        assert '"; /* literal string' in result
        assert '*/ console.log(msg)' in result
        assert '//' not in result  # Should not use single-line comment
    
    def test_literal_with_semicolon_no_more_code(self):
        """Test literal with semicolon but no more code - should use single-line comment after semicolon."""
        code = 'const msg = "this is a very long message that should be trimmed";'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place single-line comment after semicolon since no more code follows
        assert '; //' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment
    
    def test_literal_with_closing_brackets(self):
        """Test literal with closing brackets (array/object) - should place comment after brackets."""
        code = '''this.allowedExtensions = new Set([
    '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte',
    '.py', '.java', '.c', '.cpp', '.cs', '.go', '.rs'
]);'''
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place comment after closing brackets
        assert ']) // literal array' in result
        assert 'literal array' in result
        assert '/* ' not in result  # Should not use block comment
    
    def test_multiple_statements_same_line(self):
        """Test literal in complex single-line statement - should place comment after semicolon with single-line comment."""
        code = 'let a = "very long string that needs trimming", b = 42, c = true;'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place comment after semicolon with single-line comment since no code follows
        assert '; // literal string' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment
    
    def test_literal_in_function_call(self):
        """Test literal inside function call - should place comment after semicolon with single-line comment."""
        code = 'console.log("this is a very long message that should be trimmed", otherParam);'
        
        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should place comment after semicolon with single-line comment since no code follows
        assert '; // literal string' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment
    
    def _make_context(self, code: str):
        """Helper to create LightweightContext for testing."""
        from .utils import lctx
        return lctx(code)
