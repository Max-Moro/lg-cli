"""
String literal formatter.

Handles simple string truncation with inline ellipsis.
No DFS, no recursion, no nested structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lg.stats.tokenizer import TokenService
from .selector import Selection
from ..patterns import ParsedLiteral, StringProfile


@dataclass
class FormattedResult:
    """Formatted result ready for insertion into source code."""
    text: str
    start_byte: int
    end_byte: int


class StringFormatter:
    """
    Formats string literals with inline truncation.

    Simple, focused implementation:
    - Truncates string content
    - Adds ellipsis (…)

    No DFS, no nested structures, no recursion.
    """

    def __init__(self, tokenizer: TokenService):
        self.tokenizer = tokenizer

    def format(
        self,
        parsed: ParsedLiteral[StringProfile],
        selection: Selection,
        placeholder_text: Optional[str] = None,
    ) -> FormattedResult:
        """
        Format truncated string literal.

        Args:
            parsed: Parsed string literal
            selection: Selection with kept/removed content
            placeholder_text: Custom placeholder (defaults to "…")

        Returns:
            FormattedResult with truncated string and optional comment
        """
        # Simple truncation: kept_content + "…"
        if not selection.has_removals:
            # No trimming needed
            text = parsed.original_text
        else:
            # Get truncated content
            kept_content = selection.kept_elements[0].text if selection.kept_elements else ""

            # Add ellipsis
            placeholder = placeholder_text or "…"
            truncated = f"{kept_content}{placeholder}"

            # Wrap with delimiters
            text = f"{parsed.opening}{truncated}{parsed.closing}"

        return FormattedResult(
            text=text,
            start_byte=parsed.start_byte,
            end_byte=parsed.end_byte,
        )
