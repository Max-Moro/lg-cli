"""
Universal element parser for literal content.

Handles parsing of comma-separated elements with proper
handling of nested structures and string literals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ParseConfig:
    """Configuration for element parsing."""
    separator: str = ","
    kv_separator: Optional[str] = None  # For mappings: ":", "->", " to "
    preserve_whitespace: bool = False

    # Bracket pairs for nesting detection
    brackets: List[Tuple[str, str]] = field(
        default_factory=lambda: [("(", ")"), ("[", "]"), ("{", "}")]
    )

    # String delimiters to respect
    string_delimiters: List[str] = field(
        default_factory=lambda: ['"', "'", "`", '"""', "'''", 'r#"']
    )


@dataclass
class Element:
    """
    A parsed element from literal content.

    Can be a simple value, key-value pair, or nested structure.
    """
    text: str                           # Full element text (trimmed)
    raw_text: str                       # Original text with whitespace
    start_offset: int                   # Offset in content string
    end_offset: int

    # For mappings
    key: Optional[str] = None
    value: Optional[str] = None

    # For nested structures
    is_nested: bool = False

    @property
    def is_kv_pair(self) -> bool:
        """Check if this is a key-value pair."""
        return self.key is not None


class ElementParser:
    """
    Universal parser for extracting elements from literal content.

    Handles:
    - Comma-separated values
    - Nested brackets and braces
    - String literals (with escape sequences)
    - Key-value pairs for mappings
    - Multi-line content with indentation
    """

    def __init__(self, config: Optional[ParseConfig] = None):
        """Initialize parser with configuration."""
        self.config = config or ParseConfig()

    def parse(self, content: str) -> List[Element]:
        """
        Parse content into list of elements.

        Args:
            content: Content string (without opening/closing delimiters)

        Returns:
            List of parsed elements
        """
        if not content.strip():
            return []

        elements = []
        current_start = 0
        current_text = ""
        depth = 0
        in_string = False
        string_char: Optional[str] = None
        i = 0

        while i < len(content):
            char = content[i]

            # Handle string delimiters
            if not in_string:
                # Check for multi-char string delimiters first
                for delim in sorted(self.config.string_delimiters, key=len, reverse=True):
                    if content[i:].startswith(delim) and len(delim) > 1:
                        in_string = True
                        string_char = delim
                        current_text += delim
                        i += len(delim)
                        break
                else:
                    if char in ('"', "'", "`"):
                        in_string = True
                        string_char = char
                        current_text += char
                        i += 1
                    else:
                        # Not entering a string, continue below
                        pass

                if in_string:
                    continue
            else:
                # Inside string - check for closing
                if string_char and content[i:].startswith(string_char):
                    # Check for escape
                    if i > 0 and content[i-1] == '\\' and len(string_char) == 1:
                        current_text += char
                        i += 1
                        continue

                    current_text += string_char
                    i += len(string_char)
                    in_string = False
                    string_char = None
                    continue
                else:
                    current_text += char
                    i += 1
                    continue

            # Handle brackets (outside strings)
            if char in "([{":
                depth += 1
                current_text += char
                i += 1
                continue

            if char in ")]}":
                depth -= 1
                current_text += char
                i += 1
                continue

            # Handle separator at depth 0
            if depth == 0 and content[i:].startswith(self.config.separator):
                # Found element separator
                element_text = current_text.strip()
                if element_text:
                    element = self._create_element(
                        element_text,
                        current_text,
                        current_start,
                        i
                    )
                    elements.append(element)

                i += len(self.config.separator)
                current_start = i
                current_text = ""
                continue

            current_text += char
            i += 1

        # Don't forget the last element
        element_text = current_text.strip()
        if element_text:
            element = self._create_element(
                element_text,
                current_text,
                current_start,
                len(content)
            )
            elements.append(element)

        return elements

    def _create_element(
        self,
        text: str,
        raw_text: str,
        start: int,
        end: int
    ) -> Element:
        """Create an Element, detecting key-value pairs if configured."""
        key = None
        value = None
        is_nested = any(c in text for c in "([{")

        # Try to split key-value if separator is configured
        if self.config.kv_separator:
            key, value = self._split_kv(text, self.config.kv_separator)

        return Element(
            text=text,
            raw_text=raw_text,
            start_offset=start,
            end_offset=end,
            key=key,
            value=value,
            is_nested=is_nested,
        )

    def _split_kv(
        self,
        text: str,
        separator: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Split text into key-value pair.

        Only splits at the first occurrence of separator that is
        not inside nested brackets or strings.
        """
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(text):
            # Handle strings
            if not in_string and char in ('"', "'", "`"):
                in_string = True
                string_char = char
                continue
            if in_string:
                if char == string_char and (i == 0 or text[i-1] != '\\'):
                    in_string = False
                    string_char = None
                continue

            # Handle brackets
            if char in "([{":
                depth += 1
                continue
            if char in ")]}":
                depth -= 1
                continue

            # Check for separator at depth 0
            if depth == 0 and text[i:].startswith(separator):
                key = text[:i].strip()
                value = text[i + len(separator):].strip()
                return key, value

        return None, None

    def parse_with_positions(
        self,
        content: str,
        base_offset: int = 0
    ) -> List[Element]:
        """
        Parse content and return elements with absolute positions.

        Args:
            content: Content to parse
            base_offset: Offset to add to all positions

        Returns:
            List of elements with adjusted positions
        """
        elements = self.parse(content)

        for elem in elements:
            elem.start_offset += base_offset
            elem.end_offset += base_offset

        return elements
