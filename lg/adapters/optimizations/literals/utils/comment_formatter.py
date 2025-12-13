"""
Comment formatting utilities for literal optimization.

Handles:
- Comment generation with token savings
- Context-aware formatting (single-line vs block)
- Insertion point detection
"""

from __future__ import annotations

from typing import Optional

from ..patterns import ParsedLiteral, PlaceholderPosition
from ..processing.selector import SelectionBase


class CommentFormatter:
    """
    Utilities for formatting and positioning comments.

    Shared by both string and collection formatters.
    """

    def __init__(self, comment_style: tuple[str, tuple[str, str]]):
        """
        Initialize with language comment syntax.

        Args:
            comment_style: (single_line_prefix, (block_open, block_close))
        """
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

    def generate_comment(
        self,
        parsed: ParsedLiteral,
        selection: SelectionBase,
    ) -> tuple[Optional[str], Optional[int]]:
        """
        Generate external comment for literal if needed.

        Args:
            parsed: Parsed literal
            selection: Selection with kept/removed elements

        Returns:
            (comment_text, byte_position) or (None, None)
        """
        if not selection.has_removals:
            return None, None

        placeholder_position = parsed.profile.placeholder_position

        if placeholder_position == PlaceholderPosition.NONE:
            return None, None

        # For MIDDLE_COMMENT, comment is embedded in text
        if placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
            return None, None

        # Generate comment content
        tokens_saved = selection.total_tokens_saved
        category_name = parsed.profile.get_category_name()
        comment_content = self._generate_text(category_name, tokens_saved)

        return comment_content, parsed.end_byte

    def format_for_context(
        self,
        text_after_literal: str,
        comment_content: str,
    ) -> tuple[str, int]:
        """
        Format comment based on surrounding context.

        Args:
            text_after_literal: Text after literal in source
            comment_content: Raw comment text

        Returns:
            (formatted_comment, offset_from_literal_end)
        """
        line_remainder = text_after_literal.split('\n')[0]
        offset, needs_block = self._find_insertion_point(line_remainder)

        if needs_block:
            return self.format_block(comment_content), offset
        return self.format_single(comment_content), offset

    def format_single(self, content: str) -> str:
        """Format as single-line comment."""
        return f" {self.single_comment} {content}"

    def format_block(self, content: str) -> str:
        """Format as block comment."""
        return f" {self.block_comment[0]} {content} {self.block_comment[1]}"

    def _generate_text(self, category_name: str, tokens_saved: int) -> str:
        """Generate comment content text."""
        return f"literal {category_name} (−{tokens_saved} tokens)"

    def _find_insertion_point(self, line_remainder: str) -> tuple[int, bool]:
        """
        Find best insertion point for comment.

        Returns:
            (offset, needs_block_comment)
        """
        if not line_remainder.strip():
            return 0, False

        offset = 0

        # Skip closing brackets
        while offset < len(line_remainder) and line_remainder[offset] in ')]}':
            offset += 1

        # Check semicolon
        if offset < len(line_remainder) and line_remainder[offset] == ';':
            offset += 1
            after_semi = line_remainder[offset:].strip()
            if after_semi:
                return offset, True
            return offset, False

        # Check comma
        if offset < len(line_remainder) and line_remainder[offset] == ',':
            offset += 1
            after_comma = line_remainder[offset:].strip()
            if not after_comma or after_comma[0] in ')]}':
                return offset, False
            return offset, True

        # Check for code
        remaining = line_remainder[offset:].strip()
        if remaining:
            return offset, True

        return offset, False
