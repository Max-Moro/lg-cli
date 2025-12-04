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
from typing import Optional, cast

from lg.stats.tokenizer import TokenService
from .categories import (
    LiteralCategory,
    PlaceholderPosition,
    ParsedLiteral,
    TrimResult,
)
from .selector import SelectionBase, Selection, DFSSelection
from .parser import ElementParser


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
        comment, comment_byte = self._generate_comment_impl(
            parsed, selection, pattern.placeholder_position
        )

        return FormattedResult(
            text=text,
            start_byte=parsed.start_byte,
            end_byte=parsed.end_byte,
            comment=comment,
            comment_byte=comment_byte,
        )

    def format_dfs(
        self,
        parsed: ParsedLiteral,
        selection: DFSSelection,
        parser: ElementParser,
        placeholder_text: Optional[str] = None,
    ) -> FormattedResult:
        """
        Format trimmed literal with DFS-aware nested handling.

        Args:
            parsed: ParsedLiteral with structure info
            selection: DFSSelection with recursive nested selections
            parser: ElementParser for parsing nested content
            placeholder_text: Custom placeholder (or use pattern default)

        Returns:
            FormattedResult ready for insertion
        """
        pattern = parsed.pattern
        placeholder = placeholder_text or pattern.placeholder_template

        # Format based on category and layout
        if parsed.is_multiline:
            text = self._format_multiline_impl(parsed, selection, placeholder, parser)
        else:
            text = self._format_single_line_impl(parsed, selection, placeholder, parser)

        # Generate comment if needed
        comment, comment_byte = self._generate_comment_impl(
            parsed, selection, pattern.placeholder_position
        )

        return FormattedResult(
            text=text,
            start_byte=parsed.start_byte,
            end_byte=parsed.end_byte,
            comment=comment,
            comment_byte=comment_byte,
        )

    def _should_use_inline_nested(
        self,
        nested_sel: DFSSelection,
        elements_text: list,
        parent_is_multiline: bool,
        max_inline_length: int,
    ) -> bool:
        """
        Determine if nested structure should stay inline even in multiline parent.

        Key insight:
        - If structure was trimmed (has_removals=True) → originally large → multiline
        - If structure is complete (has_removals=False) and short → can stay inline

        Example: (0, 0) should stay as (0, 0), not expand to multiline.

        Args:
            nested_sel: DFSSelection for nested content
            elements_text: Formatted element texts
            parent_is_multiline: Whether parent is multiline
            max_inline_length: Maximum total length for inline format

        Returns:
            True if should use inline format
        """
        if not parent_is_multiline:
            return True  # Already inline

        # If structure was trimmed, it was large enough to need trimming → multiline
        if nested_sel.has_removals:
            return False

        # If has deeper nesting that was trimmed, use multiline
        if nested_sel.nested_selections:
            return False

        # Complete leaf structure - use inline if short enough
        total_length = sum(len(t) for t in elements_text)
        total_length += (len(elements_text) - 1) * 2  # ", " separators

        return total_length <= max_inline_length

    def _reconstruct_element_with_nested(
        self,
        elem,  # Element
        nested_sel: DFSSelection,
        parser: ElementParser,
        placeholder: str,
        is_multiline: bool = False,
        base_indent: str = "",
        elem_indent: str = "",
        inline_threshold: int = 60,
    ) -> str:
        """
        Reconstruct element with nested content formatted.

        Args:
            elem: Element with potentially nested structure
            nested_sel: DFSSelection for the nested content
            parser: ElementParser for formatting nested
            placeholder: Placeholder text
            is_multiline: Whether to format nested content as multiline
            base_indent: Base indentation for nested content
            elem_indent: Indentation for nested elements

        Returns:
            Reconstructed element text with formatted nested content
        """
        if not elem.has_nested_structure:
            return elem.text

        # Format the nested selection
        nested_elements_text = []
        for i, nested_elem in enumerate(nested_sel.kept_elements):
            if i in nested_sel.nested_selections:
                # Recursively handle deeper nesting
                nested_elem_text = self._reconstruct_element_with_nested(
                    nested_elem, nested_sel.nested_selections[i],
                    parser, placeholder, is_multiline=is_multiline,
                    base_indent=elem_indent,  # Closing bracket at current element level
                    elem_indent=elem_indent + "    ",  # Nested elements go deeper
                    inline_threshold=inline_threshold
                )
            else:
                nested_elem_text = nested_elem.text
            nested_elements_text.append(nested_elem_text)

        # Get separator from pattern (use comma as default)
        separator = ","

        # Determine if this nested level should stay inline even in multiline parent
        # Leaf structures (no deeper nesting) that are short should stay compact
        use_inline = self._should_use_inline_nested(
            nested_sel, nested_elements_text, is_multiline, inline_threshold
        )

        # Build nested content
        if not nested_elements_text:
            nested_formatted = placeholder
        elif is_multiline and not use_inline:
            # Multiline nested formatting
            lines = []
            for nested_elem_text in nested_elements_text:
                lines.append(f"{elem_indent}{nested_elem_text}{separator}")

            # Add placeholder comment if has removals
            if nested_sel.has_removals:
                tokens_saved = nested_sel.total_tokens_removed
                removed_count = nested_sel.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                lines.append(f"{elem_indent}{self.single_comment} {comment_text}")

            # Join with newlines, add opening/closing
            inner = "\n".join(lines)
            nested_formatted = f"\n{inner}\n{base_indent}"
        else:
            # Single-line nested formatting
            nested_formatted = f"{separator} ".join(nested_elements_text)
            if nested_sel.has_removals:
                tokens_saved = nested_sel.total_tokens_removed
                removed_count = nested_sel.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                nested_formatted = f"{nested_formatted}, {self.block_comment[0]} {comment_text} {self.block_comment[1]}"

        # Reconstruct element with key prefix if it's a key-value pair
        # Add wrapper for factory calls (e.g., Map.ofEntries)
        wrapper_prefix = f"{elem.nested_wrapper}" if elem.nested_wrapper else ""

        if elem.key is not None:
            # Key-value pair: use parser's kv_separator (e.g., ":" or " to ")
            kv_sep = parser.config.kv_separator if parser.config.kv_separator else ":"
            # Add space after kv_sep only if it doesn't already have trailing space
            space_after = "" if kv_sep.endswith(" ") else " "
            return f"{elem.key}{kv_sep}{space_after}{wrapper_prefix}{elem.nested_opening}{nested_formatted}{elem.nested_closing}"
        else:
            # Simple nested element
            return f"{wrapper_prefix}{elem.nested_opening}{nested_formatted}{elem.nested_closing}"

    def _generate_comment_impl(
        self,
        parsed: ParsedLiteral,
        selection: SelectionBase,
        position: PlaceholderPosition,
    ) -> tuple[Optional[str], Optional[int]]:
        """
        Unified comment generation implementation.

        Handles both flat Selection and DFS selection.

        Returns:
            (comment_text, byte_position) or (None, None)
        """
        if not selection.has_removals:
            return None, None

        if position == PlaceholderPosition.NONE:
            return None, None

        # For MIDDLE_COMMENT, comment is embedded in the text itself
        if position == PlaceholderPosition.MIDDLE_COMMENT:
            return None, None

        # Get tokens saved (different for Selection vs DFSSelection)
        if isinstance(selection, DFSSelection):
            saved = selection.total_tokens_removed
        else:
            saved = selection.tokens_removed

        # Use pattern's comment_name if set, otherwise category value
        category_name = parsed.pattern.comment_name or parsed.category.value
        # Return raw content - formatting is done by handler based on context
        comment_content = f"literal {category_name} (−{saved} tokens)"
        return comment_content, parsed.end_byte

    def _format_single_line(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format as single line (wrapper for flat selection)."""
        return self._format_single_line_impl(parsed, selection, placeholder, parser=None)

    def _format_multiline(
        self,
        parsed: ParsedLiteral,
        selection: Selection,
        placeholder: str,
    ) -> str:
        """Format as multiline (wrapper for flat selection)."""
        return self._format_multiline_impl(parsed, selection, placeholder, parser=None)

    def _format_single_line_impl(
        self,
        parsed: ParsedLiteral,
        selection: SelectionBase,
        placeholder: str,
        parser: Optional[ElementParser] = None,
    ) -> str:
        """
        Unified single-line formatting implementation.

        Handles both flat Selection and DFS selection with nested structures.
        """
        pattern = parsed.pattern
        elements_text = []

        # Process kept elements (with optional nested handling for DFS)
        if isinstance(selection, DFSSelection):
            inline_threshold = parsed.pattern.nested_inline_threshold
            for i, elem in enumerate(selection.kept_elements):
                if i in selection.nested_selections:
                    # Reconstruct with nested formatting (DFS only)
                    elem_text = self._reconstruct_element_with_nested(
                        elem, selection.nested_selections[i], parser, placeholder,
                        is_multiline=False,
                        inline_threshold=inline_threshold
                    )
                else:
                    elem_text = elem.text
                elements_text.append(elem_text)
        else:
            # Flat selection - no nested handling
            for elem in selection.kept_elements:
                elements_text.append(elem.text)

        # Handle string literals (inline placeholder)
        if parsed.category == LiteralCategory.STRING:
            if isinstance(selection, DFSSelection):
                raise ValueError(
                    f"String literals cannot use DFS selection. "
                    f"Check language descriptor configuration for {parsed.pattern.tree_sitter_types}"
                )
            return self._format_string(parsed, cast(Selection, selection))

        # Handle collections with separator
        separator = pattern.separator

        # Get tokens saved (different for Selection vs DFSSelection)
        tokens_saved = selection.total_tokens_removed if isinstance(selection, DFSSelection) else selection.tokens_removed

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

    def _format_multiline_impl(
        self,
        parsed: ParsedLiteral,
        selection: SelectionBase,
        placeholder: str,
        parser: Optional[ElementParser] = None,
    ) -> str:
        """
        Unified multiline formatting implementation.

        Handles both flat Selection and DFS selection with nested structures.
        """
        pattern = parsed.pattern
        elements = selection.kept_elements

        # Handle string literals
        if parsed.category == LiteralCategory.STRING:
            if isinstance(selection, DFSSelection):
                raise ValueError(
                    f"String literals cannot use DFS selection. "
                    f"Check language descriptor configuration for {parsed.pattern.tree_sitter_types}"
                )
            return self._format_string(parsed, cast(Selection, selection))

        base_indent = parsed.base_indent
        elem_indent = parsed.element_indent or (base_indent + "    ")
        separator = pattern.separator

        lines = []

        # Opening
        if parsed.wrapper:
            lines.append(f"{parsed.wrapper}{parsed.opening}")
        else:
            lines.append(parsed.opening)

        # Elements - group by tuple_size if specified
        tuple_size = pattern.tuple_size
        is_last_line = not selection.has_removals or pattern.placeholder_position != PlaceholderPosition.END
        allow_trailing = parsed.category != LiteralCategory.FACTORY_CALL

        # Process elements with type-aware nested handling
        if isinstance(selection, DFSSelection):
            inline_threshold = parsed.pattern.nested_inline_threshold
            for i in range(0, len(elements), tuple_size):
                group = elements[i:i + tuple_size]
                group_texts = []
                for elem_idx, elem in enumerate(group):
                    global_idx = i + elem_idx
                    if global_idx in selection.nested_selections:
                        # Reconstruct with nested formatting (DFS only)
                        elem_text = self._reconstruct_element_with_nested(
                            elem, selection.nested_selections[global_idx], parser, placeholder,
                            is_multiline=True,
                            base_indent=elem_indent,
                            elem_indent=elem_indent + "    ",
                            inline_threshold=inline_threshold
                        )
                    else:
                        elem_text = elem.text
                    group_texts.append(elem_text)
                group_text = f"{separator} ".join(group_texts)

                # Check if this is the last group
                is_last_group = (i + tuple_size >= len(elements)) and is_last_line
                trailing_sep = separator if (allow_trailing or not is_last_group) else ""
                lines.append(f"{elem_indent}{group_text}{trailing_sep}")
        else:
            # Flat selection - no nested handling
            for i in range(0, len(elements), tuple_size):
                group = elements[i:i + tuple_size]
                group_text = f"{separator} ".join(elem.text for elem in group)

                # Check if this is the last group
                is_last_group = (i + tuple_size >= len(elements)) and is_last_line
                trailing_sep = separator if (allow_trailing or not is_last_group) else ""
                lines.append(f"{elem_indent}{group_text}{trailing_sep}")

        # Get tokens saved (different for Selection vs DFSSelection)
        tokens_saved = selection.total_tokens_removed if isinstance(selection, DFSSelection) else selection.tokens_removed

        # Placeholder based on position
        if selection.has_removals:
            if pattern.placeholder_position == PlaceholderPosition.END:
                # Placeholder is last, so it gets no trailing separator for factory calls
                trailing_sep = "" if parsed.category == LiteralCategory.FACTORY_CALL else separator
                lines.append(f"{elem_indent}{placeholder}{trailing_sep}")
            elif pattern.placeholder_position == PlaceholderPosition.MIDDLE_COMMENT:
                # Build inline comment with full info (no separate comment needed)
                removed_count = selection.removed_count
                comment_text = f"… ({removed_count} more, −{tokens_saved} tokens)"
                lines.append(f"{elem_indent}{self.single_comment} {comment_text}")

        # Closing
        lines.append(f"{base_indent}{parsed.closing}")

        return "\n".join(lines)

    def _format_string(
        self,
        parsed: ParsedLiteral,
        selection: Selection
    ) -> str:
        """Format string literal with inline truncation marker."""
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
        trimmed_tokens = self.tokenizer.count_text_cached(formatted.text)

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
