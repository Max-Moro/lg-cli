"""
Result formatter for literal trimming.

Handles formatting of trimmed results with proper:
- Indentation and layout
- Placeholder positioning
- Comment generation
- Multiline/single-line handling
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .categories import (
    LiteralCategory,
    PlaceholderPosition,
    ParsedLiteral,
    TrimResult,
)
from .selector import Selection
from lg.stats.tokenizer import TokenService


@dataclass
class FormattedResult:
    """
    Formatted result ready for insertion into source code.
    """
    # Final text to insert (with all formatting)
    text: str

    # Byte range for replacement
    start_byte: int
    end_byte: int

    # Optional comment to add separately
    comment: Optional[str] = None
    comment_byte: Optional[int] = None


class ResultFormatter:
    """
    Formats trimmed literal results for source code insertion.

    Handles:
    - Layout reconstruction (indentation, newlines)
    - Placeholder positioning based on PlaceholderPosition
    - Comment generation with token savings info
    - Single-line vs multiline formatting
    """

    def __init__(
        self,
        tokenizer: TokenService,
        comment_style: tuple[str, tuple[str, str]] = ("//", ("/*", "*/"))
    ):
        """
        Initialize formatter.

        Args:
            tokenizer: Token counting service
            comment_style: (single_line_prefix, (block_open, block_close))
        """
        self.tokenizer = tokenizer
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

    def format(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder_text: Optional[str] = None,
    ) -> FormattedResult:
        """
        Format trimmed literal for source code insertion.

        Args:
            parsed: ParsedLiteral with structure info
            selection: Selection with kept/removed elements
            placeholder_text: Custom placeholder (or use pattern default)

        Returns:
            FormattedResult ready for insertion
        """
        pattern = parsed.pattern
        placeholder = placeholder_text or pattern.placeholder_template

        # Format based on category and layout
        if parsed.is_multiline:
            text = self._format_multiline(parsed, selection, placeholder)
        else:
            text = self._format_single_line(parsed, selection, placeholder)

        # Generate comment if needed
        comment, comment_byte = self._generate_comment(
            parsed, selection, pattern.placeholder_position
        )

        return FormattedResult(
            text=text,
            start_byte=parsed.start_byte,
            end_byte=parsed.end_byte,
            comment=comment,
            comment_byte=comment_byte,
        )

    def _format_single_line(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format as single line."""
        pattern = parsed.pattern
        elements_text = [e.text for e in selection.kept_elements]

        # Handle string literals (inline placeholder)
        if parsed.category == LiteralCategory.STRING:
            return self._format_string(parsed, selection, placeholder)

        # Handle collections with separator
        separator = pattern.separator

        # Build elements part
        if not elements_text:
            content = placeholder
        elif pattern.placeholder_position == PlaceholderPosition.END:
            if selection.has_removals:
                elements_text.append(placeholder)
            content = f"{separator} ".join(elements_text)
        elif pattern.placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
            # Insert block comment with full info
            if selection.has_removals and len(elements_text) >= 1:
                removed_count = selection.removed_count
                tokens_saved = selection.tokens_removed
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                comment_placeholder = f"{self.block_comment[0]} {comment_text} {self.block_comment[1]}"
                elements_text.append(comment_placeholder)
            content = f"{separator} ".join(elements_text)
        else:
            if selection.has_removals:
                elements_text.append(placeholder)
            content = f"{separator} ".join(elements_text)

        # Add wrapper for factory calls
        if parsed.wrapper:
            return f"{parsed.wrapper}{parsed.opening}{content}{parsed.closing}"

        return f"{parsed.opening}{content}{parsed.closing}"

    def _format_multiline(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format as multiline with proper indentation."""
        pattern = parsed.pattern
        elements = selection.kept_elements

        # Handle string literals
        if parsed.category == LiteralCategory.STRING:
            return self._format_string(parsed, selection, placeholder)

        base_indent = parsed.base_indent
        elem_indent = parsed.element_indent or (base_indent + "    ")
        separator = pattern.separator

        lines = []

        # Opening
        if parsed.wrapper:
            lines.append(f"{parsed.wrapper}{parsed.opening}")
        else:
            lines.append(parsed.opening)

        # Elements
        for elem in elements:
            lines.append(f"{elem_indent}{elem.text}{separator}")

        # Placeholder based on position
        if selection.has_removals:
            if pattern.placeholder_position == PlaceholderPosition.END:
                lines.append(f"{elem_indent}{placeholder}{separator}")
            elif pattern.placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
                # Build inline comment with full info (no separate comment needed)
                removed_count = selection.removed_count
                tokens_saved = selection.tokens_removed
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                lines.append(f"{elem_indent}{self.single_comment} {comment_text}")

        # Closing
        lines.append(f"{base_indent}{parsed.closing}")

        return "\n".join(lines)

    def _format_string(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format string literal with inline truncation marker."""
        content = parsed.content

        if not selection.has_removals:
            # No trimming needed
            return parsed.original_text

        # For strings, we truncate content and add …
        # The selection.kept_elements contains the truncated content pieces
        if selection.kept_elements:
            kept_content = selection.kept_elements[0].text
        else:
            kept_content = ""

        # Add truncation marker
        truncated = f"{kept_content}…"

        return f"{parsed.opening}{truncated}{parsed.closing}"

    def _generate_comment(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        position: PlaceholderPosition,
    ) -> tuple[Optional[str], Optional[int]]:
        """
        Generate comment with trimming info if needed.

        Returns:
            (comment_text, byte_position) or (None, None)
        """
        if not selection.has_removals:
            return None, None

        if position == PlaceholderPosition.NONE:
            return None, None

        # Generate comment for all positions that have removals
        # INLINE: truncation is inside the text, but still need a comment
        # END: placeholder at end, comment after closing bracket
        # AFTER_CLOSING: comment after closing bracket
        # MIDDLE_COMMENT: has embedded comment, no separate comment needed
        if position == PlaceholderPosition.MIDDLE_COMMENT:
            # Comment is embedded in the text itself
            return None, None

        saved = selection.tokens_removed
        # Use pattern's comment_name if set, otherwise category value
        category_name = parsed.pattern.comment_name or parsed.category.value
        # Return raw content - formatting is done by handler based on context
        comment_content = f"literal {category_name} (−{saved} tokens)"
        return comment_content, parsed.end_byte

    def create_trim_result(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        formatted: FormattedResult,
    ) -> TrimResult:
        """
        Create TrimResult from formatting data.

        Args:
            parsed: Original parsed literal
            selection: Element selection
            formatted: Formatted result

        Returns:
            Complete TrimResult
        """
        trimmed_tokens = self.tokenizer.count_text(formatted.text)

        return TrimResult(
            trimmed_text=formatted.text,
            original_tokens=parsed.original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=parsed.original_tokens - trimmed_tokens,
            elements_kept=selection.kept_count,
            elements_removed=selection.removed_count,
            comment_text=formatted.comment,
            comment_position=formatted.comment_byte,
        )
