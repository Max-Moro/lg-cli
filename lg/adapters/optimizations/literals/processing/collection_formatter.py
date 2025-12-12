"""
Collection literal formatter with DFS support.

Handles complex collection formatting with:
- Recursive nested structure processing
- Multiline/single-line layout
- Tuple grouping
- Inline threshold decisions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lg.stats.tokenizer import TokenService
from .selector import DFSSelection
from ..patterns import (
    ParsedLiteral,
    CollectionProfile,
    FactoryProfile,
    PlaceholderPosition,
)
from ..utils.element_parser import ElementParser
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
    Formats collection literals with DFS and nested structure support.

    Handles:
    - Recursive nested formatting
    - Multiline vs single-line layout
    - Tuple grouping (for Map.of patterns)
    - Inline threshold for nested structures
    - Separator and wrapper handling
    """

    def __init__(self, tokenizer: TokenService, comment_formatter: CommentFormatter):
        self.tokenizer = tokenizer
        self.comment_formatter = comment_formatter

    def format_dfs(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        selection: DFSSelection,
        parser: ElementParser,
        placeholder_text: Optional[str] = None,
    ) -> FormattedResult:
        """
        Format collection with DFS-aware nested handling.

        Args:
            parsed: Parsed collection literal
            selection: DFS selection with nested selections
            parser: Element parser for nested content
            placeholder_text: Custom placeholder

        Returns:
            FormattedResult with formatted collection
        """
        profile = parsed.profile
        placeholder = placeholder_text or profile.placeholder_template

        # Format based on layout
        if parsed.is_multiline:
            text = self._format_multiline(parsed, selection, parser, placeholder)
        else:
            text = self._format_single_line(parsed, selection, parser, placeholder)

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
        selection: DFSSelection,
        parser: ElementParser,
        placeholder: str,
    ) -> str:
        """Format collection as single line with DFS."""
        profile = parsed.profile

        # Collect formatted element texts with nested handling
        elements_text = self._collect_element_texts(
            selection, parser, placeholder,
            is_multiline=False,
            base_indent="",
            elem_indent="",
            inline_threshold=profile.inline_threshold
        )

        separator = profile.separator
        placeholder_position = profile.placeholder_position
        tokens_saved = selection.total_tokens_saved

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
        selection: DFSSelection,
        parser: ElementParser,
        placeholder: str,
    ) -> str:
        """Format collection as multiline with DFS."""
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
            group_texts = []

            for elem_idx, elem in enumerate(group):
                global_idx = i + elem_idx
                if global_idx in selection.nested_selections:
                    # Reconstruct with nested formatting (DFS)
                    elem_text = self._reconstruct_element_with_nested(
                        elem, selection.nested_selections[global_idx], parser, placeholder,
                        is_multiline=True,
                        base_indent=elem_indent,
                        elem_indent=elem_indent + "    ",
                        inline_threshold=profile.inline_threshold
                    )
                else:
                    elem_text = elem.text
                group_texts.append(elem_text)

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

    def _collect_element_texts(
        self,
        selection: DFSSelection,
        parser: ElementParser,
        placeholder: str,
        is_multiline: bool,
        base_indent: str,
        elem_indent: str,
        inline_threshold: int
    ) -> list[str]:
        """Collect formatted texts with DFS nested handling."""
        elements_text = []

        for i, elem in enumerate(selection.kept_elements):
            if i in selection.nested_selections:
                elem_text = self._reconstruct_element_with_nested(
                    elem, selection.nested_selections[i], parser, placeholder,
                    is_multiline=is_multiline,
                    base_indent=base_indent,
                    elem_indent=elem_indent,
                    inline_threshold=inline_threshold
                )
            else:
                elem_text = elem.text
            elements_text.append(elem_text)

        return elements_text

    def _reconstruct_element_with_nested(
        self,
        elem,
        nested_sel: DFSSelection,
        parser: ElementParser,
        placeholder: str,
        is_multiline: bool,
        base_indent: str,
        elem_indent: str,
        inline_threshold: int,
    ) -> str:
        """Recursively reconstruct element with nested content (DFS)."""
        if not elem.has_nested_structure:
            return elem.text

        # Format nested selection
        nested_elements_text = []
        for i, nested_elem in enumerate(nested_sel.kept_elements):
            if i in nested_sel.nested_selections:
                # Recursive DFS
                nested_elem_text = self._reconstruct_element_with_nested(
                    nested_elem, nested_sel.nested_selections[i],
                    parser, placeholder, is_multiline=is_multiline,
                    base_indent=elem_indent,
                    elem_indent=elem_indent + "    ",
                    inline_threshold=inline_threshold
                )
            else:
                nested_elem_text = nested_elem.text
            nested_elements_text.append(nested_elem_text)

        separator = ","

        # Decide inline vs multiline for nested
        use_inline = self._should_use_inline_nested(
            nested_sel, nested_elements_text, is_multiline, inline_threshold
        )

        # Build nested content
        if not nested_elements_text:
            nested_formatted = placeholder
        elif is_multiline and not use_inline:
            # Multiline nested
            lines = []
            for nested_elem_text in nested_elements_text:
                lines.append(f"{elem_indent}{nested_elem_text}{separator}")

            if nested_sel.has_removals and nested_sel.removed_count > 0:
                tokens_saved = nested_sel.total_tokens_saved
                removed_count = nested_sel.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                # Standalone comment: use direct formatting without leading space
                lines.append(f"{elem_indent}{self.comment_formatter.single_comment} {comment_text}")

            inner = "\n".join(lines)
            nested_formatted = f"\n{inner}\n{base_indent}"
        else:
            # Single-line nested
            nested_formatted = f"{separator} ".join(nested_elements_text)
            if nested_sel.has_removals and nested_sel.removed_count > 0:
                tokens_saved = nested_sel.total_tokens_saved
                removed_count = nested_sel.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                block_comment = self.comment_formatter.format_block(comment_text)
                nested_formatted = f"{nested_formatted}, {block_comment}"

        # Reconstruct with wrapper/key
        wrapper_prefix = f"{elem.nested_wrapper}" if elem.nested_wrapper else ""

        if elem.nested_prefix:
            return f"{{{elem.nested_prefix}{elem.nested_opening}{nested_formatted}{elem.nested_closing}}}"
        elif elem.key is not None:
            kv_sep = parser.config.kv_separator if parser.config.kv_separator else ":"
            space_after = "" if kv_sep.endswith(" ") else " "
            return f"{elem.key}{kv_sep}{space_after}{wrapper_prefix}{elem.nested_opening}{nested_formatted}{elem.nested_closing}"
        else:
            return f"{wrapper_prefix}{elem.nested_opening}{nested_formatted}{elem.nested_closing}"

    def _should_use_inline_nested(
        self,
        nested_sel: DFSSelection,
        elements_text: list,
        parent_is_multiline: bool,
        max_inline_length: int,
    ) -> bool:
        """Determine if nested structure should stay inline."""
        if not parent_is_multiline:
            return True

        if nested_sel.has_removals:
            return False

        if nested_sel.nested_selections:
            return False

        total_length = sum(len(t) for t in elements_text)
        total_length += (len(elements_text) - 1) * 2

        return total_length <= max_inline_length
