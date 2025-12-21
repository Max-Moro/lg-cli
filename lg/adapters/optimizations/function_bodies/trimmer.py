"""
Token-based trimming for function bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...code_analysis import FunctionGroup
from ...context import ProcessingContext


@dataclass
class TrimResult:
    """Result of function body trimming operation."""
    # Character positions for placeholder replacement
    placeholder_start_char: int
    placeholder_end_char: int
    # Text to keep before placeholder (may be empty)
    kept_prefix: str
    # Text to keep after placeholder (return statement + closing brace, may be empty)
    kept_suffix: str
    # Indentation for the placeholder
    indent: str
    # Number of lines removed (for placeholder text)
    lines_removed: int


class FunctionBodyTrimmer:
    """Trims function body to fit token budget."""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def should_trim(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup
    ) -> bool:
        """
        Check if function body exceeds token budget.

        Args:
            context: Processing context with tokenizer
            func_group: Function group with body info

        Returns:
            True if body needs trimming
        """
        body_text = self._get_strippable_text(context, func_group)
        if not body_text:
            return False

        token_count = context.tokenizer.count_text_cached(body_text)
        return token_count > self.max_tokens

    def trim(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup
    ) -> Optional[TrimResult]:
        """
        Trim function body to fit token budget.

        For brace-based languages:
        - Keeps some lines at the start
        - Preserves return statement at the end if present
        - Placeholder replaces the middle section

        Returns:
            TrimResult with all information needed for replacement, or None if no trimming needed
        """
        # Use pre-computed strippable range
        start_byte, end_byte = func_group.strippable_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        if start_char >= end_char:
            return None

        # Get text to trim (inner body content, without braces)
        body_text = context.raw_text[start_char:end_char]
        if not body_text.strip():
            return None

        token_count = context.tokenizer.count_text_cached(body_text)
        if token_count <= self.max_tokens:
            return None

        # Determine what to keep at the end (return statement)
        suffix_text, suffix_start_char = self._compute_suffix(context, func_group, end_char)

        # Calculate available budget for prefix
        suffix_tokens = context.tokenizer.count_text_cached(suffix_text) if suffix_text else 0
        prefix_budget = max(0, self.max_tokens - suffix_tokens)

        # Compute prefix (text to keep at start)
        prefix_text = ""
        if prefix_budget > 0:
            # Text from start to suffix (or end if no suffix)
            prefix_end = suffix_start_char if suffix_text else end_char
            available_text = context.raw_text[start_char:prefix_end]

            truncated = context.tokenizer.truncate_to_tokens(available_text, prefix_budget)
            prefix_text = self._trim_to_complete_line(truncated)

        # Compute placeholder range
        prefix_end_char = start_char + len(prefix_text) if prefix_text else start_char
        placeholder_end_char = suffix_start_char if suffix_text else end_char

        # If nothing to remove (entire body is prefix + suffix), skip trimming
        if prefix_end_char >= placeholder_end_char:
            return None

        # Count removed lines and check if there's actual content to remove
        removed_text = context.raw_text[prefix_end_char:placeholder_end_char]

        # If removed text is only whitespace, no need for placeholder
        if not removed_text.strip():
            return None

        lines_removed = removed_text.count('\n')
        if removed_text and not removed_text.endswith('\n'):
            lines_removed += 1

        # Compute indentation from first content line
        indent = self._compute_indent(body_text)

        return TrimResult(
            placeholder_start_char=prefix_end_char,
            placeholder_end_char=placeholder_end_char,
            kept_prefix=prefix_text,
            kept_suffix=suffix_text,
            indent=indent,
            lines_removed=lines_removed
        )

    def _compute_suffix(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup,
        strippable_end_char: int
    ) -> tuple[str, int]:
        """
        Compute suffix text to preserve (return statement if present).

        Returns:
            Tuple of (suffix_text, suffix_start_char)
        """
        if not func_group.return_node:
            return "", strippable_end_char

        return_node = func_group.return_node
        return_start_char = context.doc.byte_to_char_position(return_node.start_byte)
        return_end_char = context.doc.byte_to_char_position(return_node.end_byte)

        # Include the return statement line with proper line ending
        # Find line start for indentation preservation
        line_start = self._find_line_start(context.raw_text, return_start_char)

        # Get text from line start to end of strippable range
        # This includes indentation + return statement + possible trailing content
        suffix_text = context.raw_text[line_start:strippable_end_char]

        return suffix_text, line_start

    def _compute_indent(self, body_text: str) -> str:
        """
        Compute indentation from first non-empty line of body content.

        Args:
            body_text: Inner body content

        Returns:
            Indentation string (spaces/tabs)
        """
        lines = body_text.split('\n')
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                return line[:len(line) - len(stripped)]
        return ""

    def _get_strippable_text(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup
    ) -> str:
        """Get the text portion that can be stripped."""
        start_byte, end_byte = func_group.strippable_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)
        return context.raw_text[start_char:end_char]

    def _trim_to_complete_line(self, text: str) -> str:
        """Remove incomplete last line if truncation happened mid-line."""
        if not text:
            return text

        # If text ends with newline, it's complete
        if text.endswith('\n'):
            return text

        # Find last newline and cut there
        last_newline = text.rfind('\n')
        if last_newline == -1:
            # No newline found - entire text is incomplete line
            return ""

        return text[:last_newline + 1]

    def _find_line_start(self, text: str, pos: int) -> int:
        """Find the start of the line containing position pos."""
        line_start = text.rfind('\n', 0, pos)
        if line_start == -1:
            return 0
        return line_start + 1
