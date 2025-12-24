"""
Test smart comment placement for literal optimization in Python.
Ensures comments don't break code structure when placed inline.
"""

from lg.adapters.langs.python import PythonCfg
from .utils import make_adapter


class TestLiteralCommentContext:
    """Test smart comment placement for literal optimization."""
    
    def test_literal_at_end_of_line(self):
        """Test literal at end of line - should use single-line comment."""
        code = '''message = "this is a very long message that should be trimmed because it exceeds token limits"'''
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use single-line comment since nothing follows on same line
        assert '#' in result
        assert 'literal string' in result
        assert '"""' not in result  # Should not use block comment for this case
    
    def test_literal_with_code_after(self):
        """Test literal with other code after it - should use block comment."""
        code = 'message = "very long message that needs trimming"; print(message)'
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming  
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment to avoid commenting out the print statement
        assert '""" literal string' in result
        assert '""" print(message)' in result
        assert '#' not in result  # Should not use single-line comment
    
    def test_literal_multiple_assignment(self):
        """Test literal in multiple assignment - should use block comment."""
        code = 'a, b = "very long string that needs trimming", 42'
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since assignment continues
        assert '""" literal string' in result
        assert '""" 42' in result
        assert '#' not in result  # Should not use single-line comment
    
    def test_literal_in_function_call(self):
        """Test literal inside function call - should use block comment."""
        code = 'print("this is a very long message that should be trimmed", other_param)'
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since function call continues
        assert '""" literal string' in result
        assert '""" other_param' in result
        assert '#' not in result  # Should not use single-line comment
    
    def test_literal_in_list_comprehension(self):
        """Test literal in list comprehension - should use block comment."""
        code = 'result = ["very long string that should be trimmed" for x in range(3)]'
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since comprehension continues
        assert '""" literal string' in result
        assert '""" for x in range' in result
        assert '#' not in result  # Should not use single-line comment
    
    def test_literal_with_trailing_comma(self):
        """Test literal followed by comma in assignment - should use block comment."""
        code = 'a, b = "very long string that should be trimmed", "second item"'
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use block comment since assignment continues
        assert '""" literal string' in result
        assert '""" "second item"' in result
        assert '#' not in result  # Should not use single-line comment
    
    def test_multiline_literal_end_of_statement(self):
        """Test multiline literal at end of statement - should use single-line comment."""
        code = '''message = """
This is a very long multiline string that should be trimmed 
because it exceeds the token limit set for optimization
and contains unnecessary verbose content.
"""'''
        
        cfg = PythonCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)
        
        result, _ = adapter.process(self._make_context(code))
        
        # Should use single-line comment since nothing follows
        assert '#' in result
        assert 'literal string' in result
    
    def _make_context(self, code: str):
        """Helper to create LightweightContext for testing."""
        from .utils import lctx
        return lctx(code)
