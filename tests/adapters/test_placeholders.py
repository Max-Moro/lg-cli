"""
Tests for PlaceholderManager system.

Tests cover:
- Placeholder generation with different comment styles
- Placeholder collapsing logic
- Different placeholder actions (OMIT, TRUNCATE)
- Token savings display
- Indentation handling
"""

from lg.adapters.comment_style import CommentStyle, C_STYLE_COMMENTS, HASH_STYLE_COMMENTS
from lg.adapters.placeholders import PlaceholderManager, PlaceholderAction
from lg.adapters.range_edits import RangeEditor
from lg.adapters.tree_sitter_support import TreeSitterDocument


class MockDocument(TreeSitterDocument):
    """Mock TreeSitterDocument for testing without real parsing."""

    def __init__(self, text: str):
        self.text = text
        self._text_bytes = text.encode('utf-8')
        self.tree = None  # Not needed for placeholder tests

    def get_language(self):
        """Not used in placeholder tests."""
        raise NotImplementedError("Mock document doesn't need language")

    def count_removed_lines(self, start_char: int, end_char: int) -> int:
        """Count non-empty lines in the text range."""
        if start_char >= end_char:
            return 0

        removed_text = self.text[start_char:end_char]
        lines = removed_text.split('\n')
        return sum(1 for line in lines if line.strip())


def make_manager(text: str, comment_style: CommentStyle = HASH_STYLE_COMMENTS) -> PlaceholderManager:
    """
    Create PlaceholderManager with mock document and editor.

    Args:
        text: Source text
        comment_style: Comment style to use (default: Python-style #)

    Returns:
        Configured PlaceholderManager
    """
    doc = MockDocument(text)
    editor = RangeEditor(text)
    return PlaceholderManager(doc, comment_style, editor)


def apply_placeholders(pm: PlaceholderManager) -> tuple[str, dict]:
    """
    Apply placeholders and return result text and stats.

    Args:
        pm: PlaceholderManager with added placeholders

    Returns:
        Tuple of (result_text, edit_stats)
    """
    # Apply placeholders to editor (no economy check for tests)
    pm.apply_to_editor(is_economical=None)

    # Apply edits and get stats
    result_text, stats = pm.editor.apply_edits()

    return result_text, stats


class TestPlaceholderGeneration:
    """Test basic placeholder generation with different comment styles."""

    def test_omit_with_hash_comment(self):
        """Test OMIT placeholder with hash-style comments (Python)."""
        text = "def foo():\n    pass\n    return None\n"
        pm = make_manager(text, HASH_STYLE_COMMENTS)

        # Remove function body
        start = text.find(":") + 1
        end = len(text)

        pm.add_placeholder(
            element_type="function_body",
            start_char=start,
            end_char=end,
            action=PlaceholderAction.OMIT,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should have hash-style comment placeholder
        assert "# … function body omitted" in result
        # Check that at least one edit was applied
        assert stats["edits_applied"] > 0

    def test_omit_with_c_style_comment(self):
        """Test OMIT placeholder with C-style comments."""
        text = "function foo() {\n    return 42;\n}\n"
        pm = make_manager(text, C_STYLE_COMMENTS)

        # Remove function body
        start = text.find("{") + 1
        end = text.find("}")

        pm.add_placeholder(
            element_type="function_body",
            start_char=start,
            end_char=end,
            action=PlaceholderAction.OMIT,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should have C-style comment placeholder
        assert "// … function body omitted" in result

    def test_docstring_placeholder(self):
        """Test that docstring placeholders use doc markers."""
        text = '"""Original docstring."""\n'
        pm = make_manager(text, HASH_STYLE_COMMENTS)

        pm.add_placeholder(
            element_type="docstring",
            start_char=0,
            end_char=len(text),
            action=PlaceholderAction.OMIT,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Docstring should use triple-quote markers
        assert '"""' in result
        assert "docstring omitted" in result

    def test_placeholder_with_indentation(self):
        """Test that placeholder preserves indentation."""
        text = "def foo():\n    pass\n"
        pm = make_manager(text, HASH_STYLE_COMMENTS)

        start = text.find(":") + 1
        end = len(text)

        pm.add_placeholder(
            element_type="function_body",
            start_char=start,
            end_char=end,
            action=PlaceholderAction.OMIT,
            placeholder_prefix="\n    ",  # Indentation prefix
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should preserve indentation in placeholder
        assert "\n    #" in result or "    #" in result


class TestPlaceholderCollapsing:
    """Test placeholder collapsing logic."""

    def test_collapse_same_type_with_only_whitespace(self):
        """Test that same-type placeholders with only whitespace between collapse."""
        text = "import a\n\n\nimport b\n"
        pm = make_manager(text)

        # First import
        end1 = text.find("\n\n\n")
        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=end1,
            count=1,
            add_suffix_comment=True,
        )

        # Second import
        start2 = end1 + 3
        pm.add_placeholder(
            element_type="import",
            start_char=start2,
            end_char=len(text),
            count=1,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should collapse into single placeholder
        assert result.count("import") == 1  # Only one placeholder
        assert "2 imports omitted" in result

    def test_no_collapse_with_code_between(self):
        """Test that placeholders with code between don't collapse."""
        text = "from x import y\nprint(y)\nfrom a import b\n"
        pm = make_manager(text)

        # First import
        end1 = text.find("\n") + 1
        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=end1,
            add_suffix_comment=True,
        )

        # Second import (after code line)
        start2 = text.rfind("from")
        pm.add_placeholder(
            element_type="import",
            start_char=start2,
            end_char=len(text),
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should NOT collapse - two separate placeholders
        assert result.count("import omitted") == 2

    def test_no_collapse_different_indentation(self):
        """Test that placeholders at different indentation levels don't collapse."""
        text = "import a\n    import b\n"
        pm = make_manager(text)

        # First at column 0
        end1 = text.find("\n")
        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=end1,
            add_suffix_comment=True,
        )

        # Second indented
        start2 = text.find("\n") + 1
        # Skip leading spaces to get actual import start
        while start2 < len(text) and text[start2] == ' ':
            start2 += 1

        pm.add_placeholder(
            element_type="import",
            start_char=start2,
            end_char=len(text) - 1,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should NOT collapse - different indentation
        assert result.count("import omitted") == 2


class TestPlaceholderActions:
    """Test different placeholder actions (OMIT vs TRUNCATE)."""

    def test_omit_action_removes_completely(self):
        """Test that OMIT action removes content completely."""
        text = "def foo():\n    x = 1\n    return x\n"
        pm = make_manager(text)

        start = text.find(":") + 1
        end = len(text)

        pm.add_placeholder(
            element_type="function_body",
            start_char=start,
            end_char=end,
            action=PlaceholderAction.OMIT,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Original body should be gone
        assert "x = 1" not in result
        assert "return x" not in result
        # Placeholder should be present
        assert "function body omitted" in result

    def test_truncate_action_with_replacement(self):
        """Test that TRUNCATE action uses replacement text."""
        text = "very_long_literal_string_here"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="literal_string",
            start_char=0,
            end_char=len(text),
            action=PlaceholderAction.TRUNCATE,
            replacement_text="very_long…",
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should contain replacement text
        assert "very_long…" in result
        # Should have suffix comment
        assert "literal string" in result


class TestTokenSavings:
    """Test token savings display in placeholders."""

    def test_tokens_saved_format(self):
        """Test that tokens_saved uses simplified format."""
        text = '"very long string literal"'
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="literal_string",
            start_char=0,
            end_char=len(text),
            action=PlaceholderAction.OMIT,
            tokens_saved=50,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should show tokens instead of lines
        assert "−50 tokens" in result or "-50 tokens" in result
        assert "literal string" in result

    def test_no_tokens_shows_standard_format(self):
        """Test standard format when tokens_saved is None."""
        text = "import module\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=len(text),
            count=3,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should show count and type
        assert "3 imports omitted" in result
        assert "tokens" not in result


class TestPlaceholderPrefix:
    """Test placeholder prefix handling."""

    def test_prefix_preserved_in_placeholder(self):
        """Test that placeholder_prefix is preserved."""
        text = "    code\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=len(text),
            placeholder_prefix="    ",
            count=3,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should start with prefix
        assert result.startswith("    #")
        assert "3 imports omitted" in result


class TestPlaceholderCounts:
    """Test placeholder count aggregation."""

    def test_single_element_no_count_in_text(self):
        """Test that single element doesn't show count."""
        text = "import x\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=len(text),
            count=1,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should not show "1" in placeholder
        assert "import omitted" in result
        assert "1 import" not in result

    def test_multiple_elements_show_count(self):
        """Test that multiple elements show count."""
        text = "import x\nimport y\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=len(text),
            count=5,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Should show count
        assert "5 imports omitted" in result


class TestPluralization:
    """Test pluralization rules for different element types."""

    def test_class_pluralization(self):
        """Test that 'class' becomes 'classes'."""
        text = "class A:\n    pass\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="class",
            start_char=0,
            end_char=len(text),
            count=3,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        assert "3 classes omitted" in result

    def test_body_pluralization(self):
        """Test that 'body' becomes 'bodies'."""
        text = "def foo(): pass\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="function_body",
            start_char=0,
            end_char=len(text),
            count=2,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        assert "2 function bodies omitted" in result

    def test_default_pluralization(self):
        """Test default pluralization (add 's')."""
        text = "import x\n"
        pm = make_manager(text)

        pm.add_placeholder(
            element_type="import",
            start_char=0,
            end_char=len(text),
            count=3,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        assert "3 imports omitted" in result


class TestEditorIntegration:
    """Test integration with RangeEditor."""

    def test_stats_from_editor(self):
        """Test that statistics are properly returned from editor."""
        text = "def foo():\n    pass\n"
        pm = make_manager(text)

        start = text.find(":") + 1
        end = len(text)

        pm.add_placeholder(
            element_type="function_body",
            start_char=start,
            end_char=end,
            add_suffix_comment=True,
        )

        result, stats = apply_placeholders(pm)

        # Check stats structure
        assert "edits_applied" in stats
        assert "bytes_removed" in stats
        assert "bytes_added" in stats
        assert stats["edits_applied"] > 0

    def test_multiple_placeholders_applied(self):
        """Test that multiple placeholders are all applied."""
        text = "import a\nimport b\nimport c\n"
        pm = make_manager(text)

        # Add three separate placeholders
        lines = text.split("\n")
        pos = 0
        for i in range(3):
            line_end = pos + len(lines[i]) + 1
            pm.add_placeholder(
                element_type="import",
                start_char=pos,
                end_char=line_end,
                add_suffix_comment=True,
            )
            pos = line_end

        result, stats = apply_placeholders(pm)

        # All should be replaced (or collapsed)
        assert "import a" not in result
        assert "import b" not in result
        assert "import c" not in result
