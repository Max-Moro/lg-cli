"""
Token-based trimming for function bodies.
"""

from __future__ import annotations

from typing import Optional, Tuple

from ...code_analysis import FunctionGroup
from ...context import ProcessingContext


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
    ) -> Optional[Tuple[int, int, str]]:
        """
        Trim function body to fit token budget.

        Returns:
            Tuple of (start_char, end_char, trimmed_text) or None if no trimming needed
        """
        # Use pre-computed strippable range
        start_byte, end_byte = func_group.strippable_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        if start_char >= end_char:
            return None

        # Get text to trim
        body_text = context.raw_text[start_char:end_char]
        if not body_text.strip():
            return None

        token_count = context.tokenizer.count_text_cached(body_text)
        if token_count <= self.max_tokens:
            return None

        # Truncate to token budget
        truncated = context.tokenizer.truncate_to_tokens(body_text, self.max_tokens)

        # Remove incomplete last line
        truncated = self._trim_to_complete_line(truncated)

        if not truncated.strip():
            # If nothing left after trimming, return full range for placeholder
            return start_char, end_char, ""

        return start_char, end_char, truncated

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
