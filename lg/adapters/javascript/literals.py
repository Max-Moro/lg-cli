"""Shared literal optimization for JavaScript and TypeScript."""

from typing import Optional
import re
from lg.adapters.context import ProcessingContext
from lg.adapters.optimizations.literals import DefaultLiteralHandler, LiteralInfo


class JSLiteralHandler(DefaultLiteralHandler):
    """Handler for JavaScript/TypeScript template literals."""

    def trim_string_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int
    ) -> Optional[str]:
        """Trim template literals while preserving interpolation visibility."""
        # Only handle template literals (backtick strings)
        if literal_info.opening != "`":
            return None  # Not a template literal, use generic logic

        content = literal_info.content
        overhead_text = f"{literal_info.opening}{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(1, max_tokens - overhead_tokens)

        # Find interpolations ${...}
        interpolations = list(re.finditer(r'\$\{[^}]*}', content, re.DOTALL))

        if not interpolations:
            # No interpolations, use regular trimming
            trimmed = context.tokenizer.truncate_to_tokens(content, content_budget)
            return f"{trimmed}…"

        # Ensure we keep at least the start of first interpolation
        first_interp = interpolations[0]
        min_keep_length = first_interp.start() + 2  # Keep up to "${"

        # Truncate, but keep at least up to first interpolation
        trimmed = context.tokenizer.truncate_to_tokens(content, content_budget)

        # If truncation cut into or before interpolation, extend to keep "${" visible
        if len(trimmed) < min_keep_length <= len(content):
            trimmed = content[:min_keep_length]

        return f"{trimmed}…"
