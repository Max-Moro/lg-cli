"""
Placeholder and comment formatting component.

Consolidates all logic for generating and formatting placeholder comments
that annotate trimmed literals with token savings information.
"""

from __future__ import annotations


class PlaceholderCommentFormatter:
    """
    Formats placeholder comments for trimmed literals.

    Consolidates logic for:
    - Determining comment format (single-line vs block) based on context
    - Finding insertion points in source code
    - Generating comment text with token savings information
    """

    def __init__(self, comment_style: tuple[str, tuple[str, str], tuple[str, str]]):
        """
        Initialize formatter with language-specific comment syntax.

        Args:
            comment_style: Tuple of (single_line_prefix, (block_open, block_close))
                Example: ("//", ("/*", "*/")) for C-style comments
        """
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

    def format_comment_for_context(
        self,
        text_after_literal: str,
        comment_content: str,
    ) -> tuple[str, int]:
        """
        Determine comment format and insertion offset based on context.

        Analyzes the source code following a literal to decide whether to use
        single-line or block comments, and where to insert relative to the
        literal's end position.

        Args:
            text_after_literal: Text after the literal in source code
            comment_content: Raw comment text (e.g., "literal string (−42 tokens)")

        Returns:
            Tuple of (formatted_comment, offset_from_literal_end)
            - formatted_comment: Complete formatted comment with syntax
            - offset_from_literal_end: Characters to skip before inserting
                (e.g., 1 for after a semicolon)
        """
        # Get the remainder of the line after the literal
        line_remainder = text_after_literal.split('\n')[0]

        # Find insertion point and determine comment style
        offset, needs_block = self._find_comment_insertion_point(line_remainder)

        if needs_block:
            return self._format_block_comment(comment_content), offset

        return self._format_single_comment(comment_content), offset

    def generate_comment_text(
        self,
        category_name: str,
        tokens_saved: int,
    ) -> str:
        """
        Generate comment content text.

        Args:
            category_name: Type of literal (e.g., "string", "sequence", "mapping")
            tokens_saved: Number of tokens saved by optimization

        Returns:
            Comment content (e.g., "literal string (−42 tokens)")
        """
        return f"literal {category_name} (−{tokens_saved} tokens)"

    def _find_comment_insertion_point(self, line_remainder: str) -> tuple[int, bool]:
        """
        Find the best insertion point for comment.

        Analyzes trailing code after the literal to determine:
        1. How many characters to skip (offset)
        2. Whether block comment is needed

        Logic:
        - Empty line: single-line at literal end (offset=0)
        - Closing brackets: skip them, then check what follows
        - Semicolon: if nothing after, single-line OK; otherwise block
        - Comma: if followed by more elements, block needed; otherwise single-line
        - Other code: always use block comment

        Returns:
            Tuple of (offset, needs_block_comment)
            - offset: characters to skip before inserting
            - needs_block_comment: whether block comment is needed
        """
        if not line_remainder.strip():
            return 0, False  # Empty line - insert at literal end, single-line OK

        # Look for punctuation that should come before the comment
        offset = 0

        # Skip closing brackets first
        while offset < len(line_remainder) and line_remainder[offset] in ')]}':
            offset += 1

        # Check for semicolon
        if offset < len(line_remainder) and line_remainder[offset] == ';':
            offset += 1
            # Check what follows the semicolon
            after_semi = line_remainder[offset:].strip()
            if after_semi:
                # Code after semicolon - need block comment
                return offset, True
            return offset, False

        # Check for comma
        if offset < len(line_remainder) and line_remainder[offset] == ',':
            offset += 1
            after_comma = line_remainder[offset:].strip()
            # Safe if followed by closing bracket or end of line
            if not after_comma or after_comma[0] in ')]}':
                return offset, False
            # More elements follow - need block comment
            return offset, True

        # No recognized punctuation - check if there's code
        remaining = line_remainder[offset:].strip()
        if remaining:
            return offset, True  # Code present - need block comment

        return offset, False

    def _format_single_comment(self, content: str) -> str:
        """Format as single-line comment."""
        return f" {self.single_comment} {content}"

    def _format_block_comment(self, content: str) -> str:
        """Format as block comment."""
        return f" {self.block_comment[0]} {content} {self.block_comment[1]}"
