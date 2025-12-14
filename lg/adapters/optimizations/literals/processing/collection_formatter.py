"""
Collection literal formatter.

Handles collection formatting with:
- Multiline/single-line layout
- Tuple grouping
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lg.stats.tokenizer import TokenService
from .selector import Selection
from ..patterns import (
    ParsedLiteral,
    CollectionProfile,
    FactoryProfile,
    PlaceholderPosition,
)
from ..utils.comment_formatter import CommentFormatter


@dataclass
class FormattedResult:
    """Formatted result ready for insertion into source code."""
    text: str
    start_byte: int
    end_byte: int
    comment: Optional[str] = None
    comment_byte: Optional[int] = None


class CollectionFormatter:
    """
    Formats collection literals.

    Handles:
    - Multiline vs single-line layout
    - Tuple grouping (for Map.of patterns)
    - Separator and wrapper handling
    """

    def __init__(self, tokenizer: TokenService, comment_formatter: CommentFormatter):
        self.tokenizer = tokenizer
        self.comment_formatter = comment_formatter

    def format(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        selection: Selection,
        placeholder_text: Optional[str] = None,
    ) -> FormattedResult:
        """
        Format collection with simple (non-DFS) logic.

        Pipeline handles nesting via inside-out processing.

        Args:
            parsed: Parsed collection literal
            selection: Selection with kept/removed elements
            placeholder_text: Custom placeholder

        Returns:
            FormattedResult with formatted collection
        """
        profile = parsed.profile
        placeholder = placeholder_text or profile.placeholder_template

        # Format based on layout
        if parsed.is_multiline:
            text = self._format_multiline(parsed, selection, placeholder)
        else:
            text = self._format_single_line(parsed, selection, placeholder)

        # Generate comment if needed
        comment, comment_byte = self.comment_formatter.generate_comment(
            parsed, selection
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
        parsed: ParsedLiteral[CollectionProfile],
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format collection as single line."""
        profile = parsed.profile
        elements = selection.kept_elements

        separator = profile.separator
        placeholder_position = profile.placeholder_position
        tokens_saved = selection.total_tokens_saved

        # Collect element texts
        elements_text = [elem.text for elem in elements]

        # Build content
        if not elements_text:
            content = placeholder
        elif placeholder_position == PlaceholderPosition.END:
            if selection.removed_count > 0:
                elements_text.append(placeholder)
            content = f"{separator} ".join(elements_text)
        elif placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
            if selection.removed_count > 0 and len(elements_text) >= 1:
                removed_count = selection.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                block_comment = self.comment_formatter.format_block(comment_text)
                elements_text.append(block_comment)
            content = f"{separator} ".join(elements_text)
        else:
            if selection.removed_count > 0:
                elements_text.append(placeholder)
            content = f"{separator} ".join(elements_text)

        # Wrap with delimiters and wrapper
        if parsed.wrapper:
            return f"{parsed.wrapper}{parsed.opening}{content}{parsed.closing}"
        return f"{parsed.opening}{content}{parsed.closing}"

    def _format_multiline(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format collection as multiline."""
        profile = parsed.profile
        elements = selection.kept_elements

        base_indent = parsed.base_indent
        elem_indent = parsed.element_indent or (base_indent + "    ")
        separator = profile.separator
        placeholder_position = profile.placeholder_position
        tuple_size = profile.tuple_size if isinstance(profile, FactoryProfile) else 1

        lines = []

        # Opening
        if parsed.wrapper:
            lines.append(f"{parsed.wrapper}{parsed.opening}")
        else:
            lines.append(parsed.opening)

        # Elements - group by tuple_size
        is_last_line = not selection.has_removals or placeholder_position != PlaceholderPosition.END
        allow_trailing = not isinstance(profile, FactoryProfile)

        for i in range(0, len(elements), tuple_size):
            group = elements[i:i + tuple_size]
            group_texts = [elem.text for elem in group]
            group_text = f"{separator} ".join(group_texts)

            # Trailing separator logic
            is_last_group = (i + tuple_size >= len(elements)) and is_last_line
            trailing_sep = separator if (allow_trailing or not is_last_group) else ""
            lines.append(f"{elem_indent}{group_text}{trailing_sep}")

        # Placeholder based on position
        tokens_saved = selection.total_tokens_saved
        if selection.removed_count > 0:
            if placeholder_position == PlaceholderPosition.END:
                trailing_sep = "" if isinstance(profile, FactoryProfile) else separator
                lines.append(f"{elem_indent}{placeholder}{trailing_sep}")
            elif placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
                removed_count = selection.removed_count
                if removed_count > 0:
                    comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                    # Standalone comment: use direct formatting without leading space
                    lines.append(f"{elem_indent}{self.comment_formatter.single_comment} {comment_text}")

        # Closing
        lines.append(f"{base_indent}{parsed.closing}")

        return "\n".join(lines)

