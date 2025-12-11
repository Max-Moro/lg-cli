"""
Literal parser for Tree-sitter based literal extraction.

Handles parsing of literals from Tree-sitter nodes:
- Extracting text and boundaries
- Detecting wrappers and delimiters
- Creating ParsedLiteral structures
- No budget or placeholder logic
"""

from __future__ import annotations

from typing import Optional, Union

from ..patterns import (
    ParsedLiteral,
    P,
)


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

    def parse_literal_with_profile(
        self,
        text: str,
        profile: P,
        start_byte: int,
        end_byte: int,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[ParsedLiteral[P]]:
        """
        Parse a literal from source text using a known profile.

        Args:
            text: Full literal text including delimiters
            profile: Profile (StringProfile, SequenceProfile, etc.) that matched this node
            start_byte: Start position in source
            end_byte: End position in source
            base_indent: Indentation of line containing literal
            element_indent: Indentation for elements inside

        Returns:
            ParsedLiteral or None if not recognized
        """
        # Detect wrapper (some patterns like Go composite_literal need it)
        wrapper = self._detect_wrapper_from_profile(text, profile)

        # Detect opening/closing using profile attributes
        opening = self._get_delimiter(profile.opening, text)
        closing = self._get_delimiter(profile.closing, text)

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
            opening=opening,
            closing=closing,
            content=content,
            wrapper=wrapper,
            is_multiline=is_multiline,
            base_indent=base_indent,
            element_indent=element_indent,
            profile=profile,
        )


    def _get_delimiter(self, delimiter: Union[str, callable], text: str) -> str:
        """
        Get delimiter from profile attribute (can be static or callable).

        Args:
            delimiter: Static string or callable that determines delimiter
            text: Text to use for callable evaluation

        Returns:
            The delimiter string
        """
        if callable(delimiter):
            return delimiter(text)
        return delimiter

    def _detect_wrapper_from_profile(self, text: str, profile: P) -> Optional[str]:
        """
        Detect wrapper prefix using opening delimiter from the known profile.

        Examples:
        - Java: "List.of(...)" -> "List.of" (opening: "(")
        - Go: "[]string{...}" -> "[]string" (opening: "{")
        - Kotlin: "mapOf(...)" -> "mapOf" (opening: "(")

        Args:
            text: Full literal text
            profile: The profile that matched this literal

        Returns:
            Wrapper string or None
        """
        stripped = text.strip()

        # Get opening and closing delimiters from the profile
        opening = self._get_delimiter(profile.opening, text)
        closing = self._get_delimiter(profile.closing, text)

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

    @staticmethod
    def detect_base_indent(text: str, byte_pos: int) -> str:
        """
        Determine indentation of the line containing the literal.

        Extracts the whitespace characters (spaces and tabs) from the beginning
        of the line up to the position where the literal starts.

        Args:
            text: Full source text
            byte_pos: Byte position where literal starts

        Returns:
            Indentation string (spaces/tabs)

        Example:
            >>> text = "def foo():\\n    x = [1, 2, 3]"
            >>> pos = text.find('[')
            >>> LiteralParser.detect_base_indent(text, pos)
            '    '
        """
        line_start = text.rfind('\n', 0, byte_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        indent = ""
        for i in range(line_start, min(byte_pos, len(text))):
            if text[i] in ' \t':
                indent += text[i]
            else:
                break

        return indent

    @staticmethod
    def detect_element_indent(literal_text: str, base_indent: str) -> str:
        """
        Determine indentation for elements inside a multiline literal.

        Scans the literal's content to find the indentation level used for
        its elements. If the literal is single-line or indentation cannot
        be determined, returns base_indent + 4 spaces.

        Args:
            literal_text: Full literal text (including delimiters)
            base_indent: Base indentation of the line containing the literal

        Returns:
            Element indentation string

        Example:
            >>> literal = "[\\n    1,\\n    2\\n]"
            >>> LiteralParser.detect_element_indent(literal, "")
            '    '
        """
        lines = literal_text.split('\n')
        if len(lines) < 2:
            return base_indent + "    "

        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith((']', '}', ')')):
                indent = ""
                for char in line:
                    if char in ' \t':
                        indent += char
                    else:
                        break
                if indent:
                    return indent

        return base_indent + "    "

    def parse_from_node(
        self,
        node,
        doc,
        source_text: str,
        profile: P
    ) -> Optional[ParsedLiteral[P]]:
        """
        High-level API: parse literal with automatic parameter detection.

        This method automatically determines all parameters (indentation, boundaries)
        from the Tree-sitter node and source text. Pipeline should use this method
        instead of the low-level parse_literal_with_profile.

        Args:
            node: Tree-sitter node representing the literal
            doc: Tree-sitter document
            source_text: Full source text
            profile: Profile that matched this literal

        Returns:
            ParsedLiteral or None if parsing failed

        Example:
            >>> parsed = parser.parse_from_node(node, doc, source_text, profile)
            >>> if parsed:
            ...     print(f"Literal tokens: {parsed.original_tokens}")
        """
        text = doc.get_node_text(node)
        start_byte, end_byte = doc.get_node_range(node)

        # Automatically determine indentation
        base_indent = self.detect_base_indent(source_text, start_byte)
        element_indent = self.detect_element_indent(text, base_indent)

        # Delegate to low-level method
        return self.parse_literal_with_profile(
            text, profile, start_byte, end_byte,
            base_indent, element_indent
        )
