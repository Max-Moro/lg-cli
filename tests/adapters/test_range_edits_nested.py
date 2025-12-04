"""
Tests for nested edits handling in RangeEditor.

Scenario: Two-pass optimization where narrow edits (strings) are applied first,
then wider edits (collections) are applied, but narrow edits should be preserved.
"""

import pytest
from lg.adapters.range_edits import RangeEditor


class TestNestedEditsPreservation:
    """Test that wider edits can preserve and compose with nested narrower edits."""

    def test_narrow_edit_preserved_inside_wide_edit(self):
        """
        When a wide replacement contains a narrow replacement,
        the narrow replacement should be applied to the wide replacement's content.
        """
        original = 'const config = { apiKey: "very long string that needs trimming", timeout: 5000 };'

        editor = RangeEditor(original)

        # Pass 1: Replace the long string (narrow edit)
        # String is at positions 25-63
        editor.add_replacement(25, 63, '"very l…"', "literal_trimmed")
        editor.add_insertion(63, ' // literal string (−10 tokens)', "literal_comment")

        # Pass 2: Replace the entire object (wide edit)
        # Object is at positions 15-80 (without semicolon)
        # This should compose with the narrow string edit from Pass 1
        wide_replacement = '{\n    apiKey: "very long string that needs trimming",\n    // … (1 more, −5 tokens)\n}'
        success = editor.add_replacement_composing_nested(15, 80, wide_replacement, "literal_trimmed")

        # Should succeed and compose
        assert success is True

        result, _ = editor.apply_edits()

        # Should see BOTH placeholders:
        # - The trimmed string with INLINE comment from narrow edit
        # - Object placeholder comment from wide edit (MIDDLE_COMMENT style)
        assert '"very l…"' in result
        assert '// literal string' in result
        assert '// … (1 more' in result


    def test_wide_edit_without_nested_edits_applied_normally(self):
        """
        When a wide replacement has no nested edits, it should be applied normally.
        """
        original = 'const data = { items: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] };'

        editor = RangeEditor(original)

        # No narrow edits added

        # Wide edit for the array (22, 53)
        wide_replacement = '[1, 2, 3, /* ... (7 more) */]'
        success = editor.add_replacement_composing_nested(22, 53, wide_replacement, "literal_trimmed")

        # Should succeed because no nested edits
        assert success is True

        result, _ = editor.apply_edits()

        assert 'const data = { items: [1, 2, 3, /* ... (7 more) */] };' == result


    def test_multiple_narrow_edits_inside_wide_edit(self):
        """
        Multiple narrow edits inside a wide edit should be composed where possible.

        If DFS already replaced some elements with placeholders, narrow edits for those
        elements are skipped (they were already handled by DFS).
        """
        original = 'const obj = { str1: "long string 1", str2: "long string 2" };'

        editor = RangeEditor(original)

        # Pass 1: Replace both strings
        editor.add_replacement(20, 35, '"long s…"', "literal_trimmed")
        editor.add_replacement(44, 59, '"long s…"', "literal_trimmed")

        # Pass 2: Replace the entire object - should compose with narrow edits
        # Note: DFS already replaced str2 with placeholder "// … (1 more)"
        wide_replacement = '{\n    str1: "long string 1",\n    // … (1 more)\n}'
        success = editor.add_replacement_composing_nested(12, 61, wide_replacement, "literal_trimmed")

        # Should succeed
        assert success is True

        result, _ = editor.apply_edits()

        # First narrow edit should be visible (applied to str1)
        # Second narrow edit is skipped (str2 was already replaced by DFS)
        assert result.count('"long s…"') == 1
        assert '// … (1 more)' in result  # DFS placeholder present


    def test_wide_edit_partially_overlapping_not_containing(self):
        """
        Wide edit that overlaps but doesn't fully contain a narrow edit
        should use existing "wider wins" policy.
        """
        original = 'const x = "string"; const y = "another";'

        editor = RangeEditor(original)

        # Narrow edit
        editor.add_replacement(10, 18, '"str…"', "literal_trimmed")

        # Wide edit that partially overlaps (not containing)
        # This should use the existing policy (wider wins)
        editor.add_replacement(0, 19, 'const x = "new value";', "other")

        result, _ = editor.apply_edits()

        # Wider edit should win (existing behavior)
        assert result == 'const x = "new value"; const y = "another";'


    def test_composable_edit_with_nested_string_and_comment(self):
        """
        Test the alternative approach: composable edits that apply nested edits
        on top of wide replacement content.
        """
        original = 'const obj = { key: "very long string" };'

        editor = RangeEditor(original)

        # Pass 1: String replacement
        editor.add_replacement(19, 38, '"very l…"', "literal_trimmed")
        editor.add_insertion(38, ' // literal string', "literal_comment")

        # Pass 2: Object replacement with composition
        wide_replacement = '{\n    key: "very long string"\n}'

        # This should:
        # 1. Take wide_replacement
        # 2. Apply narrow edits (19, 38) -> (7, 26) in wide_replacement coordinates
        # 3. Result in: '{\n    key: "very l…" // literal string\n}'
        success = editor.add_replacement_composing_nested(
            12, 40,
            wide_replacement,
            "literal_trimmed"
        )

        assert success is True

        result, _ = editor.apply_edits()

        # Should see both:
        # - Trimmed string from narrow edit
        # - Structure from wide edit (newlines, indentation)
        assert '"very l…"' in result
        assert '// literal string' in result
        assert result.count('\n') >= 2  # Multi-line from wide edit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
