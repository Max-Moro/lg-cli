"""
Literal parser for Tree-sitter based literal extraction.

Handles parsing of literals from Tree-sitter nodes:
- Extracting text and boundaries
- Detecting wrappers and delimiters
- Creating ParsedLiteral structures
- No budget or placeholder logic
"""

from __future__ import annotations

from typing import Optional
import re

from ..categories import ParsedLiteral, LiteralPattern, LiteralCategory


class LiteralParser:
    """
    Parser for extracting literal information from source code.

    Responsibilities:
    - Parse literals from text with known patterns
    - Detect opening/closing delimiters
    - Extract content and wrapper prefixes
    - Create ParsedLiteral structures

    Does NOT handle:
    - Token budgeting
    - Placeholder generation
    - Element selection
    - Result formatting
    """

    def __init__(self, tokenizer):
        """
        Initialize parser.

        Args:
            tokenizer: Token counting service
        """
        self.tokenizer = tokenizer

    def parse_literal_with_pattern(
        self,
        text: str,
        pattern: LiteralPattern,
        start_byte: int,
        end_byte: int,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[ParsedLiteral]:
        """
        Parse a literal from source text using a known pattern.

        Args:
            text: Full literal text including delimiters
            pattern: LiteralPattern that matched this node
            start_byte: Start position in source
            end_byte: End position in source
            base_indent: Indentation of line containing literal
            element_indent: Indentation for elements inside

        Returns:
            ParsedLiteral or None if not recognized
        """
        # Detect wrapper (some patterns like Go composite_literal need it)
        wrapper = self._detect_wrapper_from_text(text, pattern)

        # Detect opening/closing
        opening = pattern.get_opening(text)
        closing = pattern.get_closing(text)

        # Extract content (pass wrapper to skip past it when searching for opening)
        content = self._extract_content(text, opening, closing, wrapper)

        if content is None:
            return None

        # Detect layout
        is_multiline = "\n" in text

        # Count tokens
        original_tokens = self.tokenizer.count_text_cached(text)

        return ParsedLiteral(
            original_text=text,
            start_byte=start_byte,
            end_byte=end_byte,
            original_tokens=original_tokens,
            category=pattern.category,
            opening=opening,
            closing=closing,
            content=content,
            wrapper=wrapper,
            is_multiline=is_multiline,
            base_indent=base_indent,
            element_indent=element_indent,
            pattern=pattern,
        )

    def _detect_wrapper_from_text(self, text: str, pattern: LiteralPattern) -> Optional[str]:
        """
        Detect wrapper prefix using opening delimiter from the known pattern.

        Examples:
        - Java: "List.of(...)" -> "List.of" (opening: "(")
        - Go: "[]string{...}" -> "[]string" (opening: "{")
        - Kotlin: "mapOf(...)" -> "mapOf" (opening: "(")

        Args:
            text: Full literal text
            pattern: The pattern that matched this literal

        Returns:
            Wrapper string or None
        """
        stripped = text.strip()

        # Get opening and closing delimiters from the known pattern
        opening = pattern.get_opening(text) if callable(pattern.opening) else pattern.opening
        closing = pattern.get_closing(text) if callable(pattern.closing) else pattern.closing

        # If text starts with opening delimiter, there's no wrapper
        if stripped.startswith(opening):
            return None

        # Find position of opening delimiter
        pos = stripped.find(opening)
        if pos > 0:
            # Extract wrapper as-is (preserve formatting)
            wrapper = stripped[:pos]

            # Include empty bracket pairs that are part of type/wrapper syntax
            if stripped[pos:pos+2] == opening + closing:
                wrapper += opening + closing

            return wrapper

        return None

    def _extract_content(
        self,
        text: str,
        opening: str,
        closing: str,
        wrapper: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract content between opening and closing delimiters.

        Args:
            text: Full literal text
            opening: Opening delimiter
            closing: Closing delimiter
            wrapper: Optional wrapper prefix to skip

        Returns:
            Content string or None if delimiters not found
        """
        stripped = text.strip()

        # Handle wrapper prefix (e.g., "vec!" in "vec![...]", type prefixes)
        if not stripped.startswith(opening):
            # If wrapper is known, start search AFTER wrapper to avoid
            # finding opening brackets that are part of wrapper itself
            if wrapper:
                search_from = len(wrapper)
            else:
                search_from = 0

            # Find opening position
            open_pos = stripped.find(opening, search_from)
            if open_pos == -1:
                return None
            stripped = stripped[open_pos:]

        if not stripped.startswith(opening) or not stripped.endswith(closing):
            return None

        return stripped[len(opening):-len(closing)]
