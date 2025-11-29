"""
Test smart comment placement for literal optimization in JavaScript.
Ensures comments don't break code structure when placed inline.
"""

from lg.adapters.javascript import JavaScriptCfg
from .utils import lctx, make_adapter

class TestLiteralCommentContext:
    """Test smart comment placement for literal optimization."""

    def test_literal_with_semicolon_immediate(self):
        """Test literal with semicolon immediately after - should use single-line comment after semicolon."""
        code = 'const message = "very long string that should be trimmed for optimization purposes and exceed the token limit";'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place single-line comment after semicolon
        assert '; //' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment

    def test_literal_with_code_after(self):
        """Test literal with other code after it - should place comment after semicolon with block comment."""
        code = 'function getLastLogin() { date = "2024-01-15T10:30:00Z"; return date; }'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment after semicolon with block comment to avoid commenting out the return statement
        assert '"; /* literal string' in result
        assert '*/ return date' in result
        assert '//' not in result  # Should not use single-line comment

    def test_literal_at_end_of_line(self):
        """Test literal at end of line - should use single-line comment."""
        code = '''const message = "this is a very long message that should be trimmed because it exceeds token limits"'''

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should use single-line comment since nothing follows on same line
        assert '//' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment

    def test_literal_with_closing_brace(self):
        """Test literal followed by closing brace - should use block comment since there's code after semicolon."""
        code = 'function getDate() { return "2024-01-15T10:30:00Z very long timestamp"; }'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should use block comment since there's code (closing brace) after semicolon
        assert '/* literal string' in result
        assert '*/ }' in result
        assert '//' not in result  # Should not use single-line comment

    def test_literal_with_semicolon_and_more_code(self):
        """Test literal with semicolon followed by more code - should place comment after semicolon with block comment."""
        code = 'const msg = "this is a very long message that should be trimmed"; console.log(msg);'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment after semicolon with block comment to avoid commenting out following code
        assert '"; /* literal string' in result
        assert '*/ console.log(msg)' in result
        assert '//' not in result  # Should not use single-line comment

    def test_literal_with_semicolon_no_more_code(self):
        """Test literal with semicolon but no more code - should use single-line comment after semicolon."""
        code = 'const msg = "this is a very long message that should be trimmed";'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

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

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment after closing brackets
        assert ']) // literal array' in result
        assert 'literal array' in result
        assert '/* ' not in result  # Should not use block comment

    def test_multiple_statements_same_line(self):
        """Test literal in complex single-line statement - should place comment after semicolon with single-line comment."""
        code = 'let a = "very long string that needs trimming", b = 42, c = true;'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment after semicolon with single-line comment since no code follows
        assert '; // literal string' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment

    def test_literal_in_function_call(self):
        """Test literal inside function call - should place comment after semicolon with single-line comment."""
        code = 'console.log("this is a very long message that should be trimmed", otherParam);'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment after semicolon with single-line comment since no code follows
        assert '; // literal string' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment

    def test_template_literal_multiline(self):
        """Test template literal multiline - should preserve backticks and use appropriate comment style."""
        code = '''const html = `<div class="container">
    <h1>This is a very long heading that should be trimmed</h1>
    <p>Another long paragraph that exceeds the token limit</p>
</div>`;'''

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place single-line comment after semicolon
        assert '; //' in result
        assert 'literal' in result
        assert '/* ' not in result  # Should not use block comment

    def test_literal_in_arrow_function_return(self):
        """Test literal in arrow function return - should handle correctly."""
        code = 'const getMessage = () => "this is a very long message that should be trimmed for optimization";'

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place single-line comment after semicolon
        assert '; //' in result
        assert 'literal string' in result
        assert '/* ' not in result  # Should not use block comment

    def test_literal_in_object_property(self):
        """Test literal as object property value - should handle correctly."""
        code = '''const config = {
    apiKey: "this is a very long API key string that should be trimmed for optimization purposes",
    timeout: 5000
};'''

        cfg = JavaScriptCfg()
        cfg.literals.max_tokens = 5  # Force trimming
        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code))

        # Should place comment appropriately without breaking object syntax
        assert 'literal string' in result
