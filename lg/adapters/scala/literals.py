"""Scala-specific literal optimization."""

import re
from typing import Optional

from ..optimizations.literals import DefaultLiteralHandler, LiteralInfo


class ScalaLiteralHandler(DefaultLiteralHandler):
    """Handler for Scala interpolated strings (s"...", f"...", raw"...", etc.)."""

    def analyze_literal_structure(
        self,
        stripped: str,
        is_multiline: bool,
        language: str
    ) -> Optional[LiteralInfo]:
        """
        Analyze Scala interpolated strings.

        Scala supports string interpolation with prefixes:
        - s"..." or s\"\"\"...\"\"\" - standard interpolation
        - f"..." or f\"\"\"...\"\"\" - formatted interpolation
        - raw"..." or raw\"\"\"...\"\"\" - raw interpolation
        - custom"..." - user-defined interpolators

        Args:
            stripped: Stripped literal text
            is_multiline: Whether literal spans multiple lines
            language: Language identifier

        Returns:
            LiteralInfo if this is an interpolated string, None otherwise
        """
        # Pattern: <interpolator><quote>...<quote>
        # Interpolator: identifier starting with letter/underscore
        # Quote: """ or " or '
        match = re.match(r'^([a-zA-Z_]\w*)("""|"|\')', stripped)

        if not match:
            return None  # Not an interpolated string, use generic logic

        interpolator = match.group(1)
        quote_style = match.group(2)

        # Opening includes interpolator prefix
        opening = interpolator + quote_style
        closing = quote_style

        # Extract content between quotes
        content_start = len(opening)
        content_end = stripped.rfind(closing)

        if content_end > content_start:
            content = stripped[content_start:content_end]
            return LiteralInfo("string", opening, closing, content, is_multiline, language)

        # Edge case: empty interpolated string
        if content_end == content_start:
            return LiteralInfo("string", opening, closing, "", is_multiline, language)

        return None
