"""
Universal element parser for literal content.

Handles parsing of comma-separated elements with proper
handling of nested structures and string literals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..descriptor import LanguageLiteralDescriptor
from ..patterns import CollectionProfile, MappingProfile, FactoryProfile


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

    # Factory method wrappers (for detecting () as nested in factory calls)
    # Examples: ["List.of", "Map.of", "Map.ofEntries", "Set.of"]
    factory_wrappers: List[str] = field(default_factory=list)

    @classmethod
    def from_profile_and_descriptor(
        cls,
        profile: CollectionProfile,
        descriptor: LanguageLiteralDescriptor
    ) -> ParseConfig:
        """
        Создать ParseConfig из профиля и дескриптора.

        Автоматически извлекает:
        - separator из профиля
        - kv_separator из профиля (если MappingProfile/FactoryProfile)
        - factory_wrappers из дескриптора

        Args:
            profile: CollectionProfile (SequenceProfile, MappingProfile, FactoryProfile)
            descriptor: LanguageLiteralDescriptor

        Returns:
            Сконфигурированный ParseConfig
        """
        separator = profile.separator
        kv_separator = None

        if isinstance(profile, (MappingProfile, FactoryProfile)):
            kv_separator = profile.kv_separator

        factory_wrappers = ElementParser.collect_factory_wrappers_from_descriptor(descriptor)

        return cls(
            separator=separator,
            kv_separator=kv_separator,
            preserve_whitespace=False,
            factory_wrappers=factory_wrappers,
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
    nested_opening: Optional[str] = None    # Opening bracket: {, [, (
    nested_closing: Optional[str] = None    # Closing bracket: }, ], )
    nested_content: Optional[str] = None    # Content inside brackets
    nested_wrapper: Optional[str] = None    # Wrapper for factory calls: List.of, Map.ofEntries
    nested_prefix: Optional[str] = None     # Prefix before nested structure (for tuple elements like {"key", {...}})
    is_multiline: bool = False              # Whether this element spans multiple lines

    @property
    def is_kv_pair(self) -> bool:
        """Check if this is a key-value pair."""
        return self.key is not None

    @property
    def has_nested_structure(self) -> bool:
        """Check if this element has a parseable nested structure."""
        return self.is_nested and self.nested_content is not None

    @property
    def is_multiline_nested(self) -> bool:
        """Check if this is a multiline nested structure suitable for DFS."""
        return self.has_nested_structure and self.is_multiline


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

    def __init__(self, config: ParseConfig):
        """Initialize parser with configuration."""
        self.config = config

    @staticmethod
    def collect_factory_wrappers_from_descriptor(descriptor: LanguageLiteralDescriptor) -> List[str]:
        """
        Извлечь все factory wrappers из дескриптора языка.

        Собирает wrappers из:
        - factory_profiles (wrapper_match regex)
        - mapping_profiles (wrapper_match regex, если есть)
        - nested_factory_wrappers (дополнительные wrappers)

        Args:
            descriptor: LanguageLiteralDescriptor

        Returns:
            List уникальных factory wrappers
        """
        wrappers = []

        # Collect from all profiles (filter by type)
        for profile in descriptor.profiles:
            if isinstance(profile, FactoryProfile):
                if profile.wrapper_match:
                    regex = profile.wrapper_match.rstrip("$")
                    if regex.startswith("(") and regex.endswith(")"):
                        regex = regex[1:-1]
                    alternatives = regex.split("|")
                    for alt in alternatives:
                        wrapper = alt.replace("\\.", ".")
                        if wrapper and wrapper not in wrappers:
                            wrappers.append(wrapper)
            elif isinstance(profile, MappingProfile):
                if profile.wrapper_match:
                    regex = profile.wrapper_match.rstrip("$")
                    if regex.startswith("(") and regex.endswith(")"):
                        regex = regex[1:-1]
                    alternatives = regex.split("|")
                    for alt in alternatives:
                        wrapper = alt.replace("\\.", ".")
                        if wrapper and wrapper not in wrappers:
                            wrappers.append(wrapper)

        # Add additional wrappers from descriptor
        for wrapper in descriptor.nested_factory_wrappers:
            if wrapper not in wrappers:
                wrappers.append(wrapper)

        return wrappers

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
        """Create an Element, detecting key-value pairs and nested structures."""
        key = None
        value = None
        is_nested = False
        nested_opening = None
        nested_closing = None
        nested_content = None

        # Try to split key-value if separator is configured
        if self.config.kv_separator:
            key, value = self._split_kv(text, self.config.kv_separator)

        # Determine what to analyze for nesting: value (if kv pair) or whole text
        check_text = value if value is not None else text

        # Extract nested structure info
        nested_info = self._extract_nested_info(check_text)
        nested_prefix = None
        if nested_info:
            is_nested = True
            nested_opening, nested_closing, nested_content, nested_wrapper, nested_prefix = nested_info
        else:
            nested_wrapper = None

        # Detect if this element is multiline (check actual element text, not whitespace between elements)
        is_multiline = '\n' in text

        return Element(
            text=text,
            raw_text=raw_text,
            start_offset=start,
            end_offset=end,
            key=key,
            value=value,
            is_nested=is_nested,
            nested_opening=nested_opening,
            nested_closing=nested_closing,
            nested_content=nested_content,
            nested_wrapper=nested_wrapper,
            nested_prefix=nested_prefix,
            is_multiline=is_multiline,
        )

    def _extract_nested_info(
        self,
        text: str
    ) -> Optional[Tuple[str, str, str, Optional[str], Optional[str]]]:
        """
        Extract nested structure info from text.

        Returns:
            Tuple of (opening, closing, content, wrapper, prefix) or None if not nested
            wrapper is set for factory calls (e.g., "Map.ofEntries")
            prefix is set for tuple-like elements (e.g., `"database", ` from `{"database", {...}}`)
        """
        text = text.strip()

        # Check for factory method calls with () if configured
        # This allows DFS to descend into nested factory calls like Map.ofEntries(...)
        if self.config.factory_wrappers:
            for wrapper in self.config.factory_wrappers:
                if text.startswith(wrapper + "(") and text.endswith(")"):
                    # Extract content between parentheses
                    content = text[len(wrapper) + 1:-1]
                    return "(", ")", content, wrapper, None

        # Check for each bracket type (only { and [ for nested, not ())
        # Parentheses () are typically function calls, not data structures
        bracket_pairs = [("{", "}"), ("[", "]")]

        for opening, closing in bracket_pairs:
            if text.startswith(opening) and text.endswith(closing):
                # Extract content between brackets
                content = text[len(opening):-len(closing)]

                # Special case: for tuple-like elements with nested collection as second element
                # E.g., {"key", {...}} -> extract the inner {...} as nested_content
                # This is useful for C/C++ initializer_list (std::map<string, map<string, T>>)
                # and similar tuple-based structures in other languages
                # ONLY apply if this is NOT a key-value structure (check for kv_separator at depth 0)
                kv_sep = self.config.kv_separator or ":"  # Fallback to ":" if not configured
                if opening == "{" and "," in content and not self._has_kv_separator_at_depth_zero(content, kv_sep):
                    # Check if there's another nested { after the comma
                    inner_nested = self._extract_deepest_nested(content, opening, closing)
                    if inner_nested:
                        inner_opening, inner_closing, inner_content, inner_wrapper, inner_prefix = inner_nested
                        return inner_opening, inner_closing, inner_content, inner_wrapper, inner_prefix

                return opening, closing, content, None, None

        # Check if text contains a nested structure (not at boundaries)
        # Only for { and [ - skip () as those are usually function calls
        for opening, closing in bracket_pairs:
            open_pos = text.find(opening)
            if open_pos != -1:
                # Skip empty bracket pairs that are part of type/wrapper syntax
                # (e.g., empty braces in composite type declarations)
                if text[open_pos:open_pos+2] == opening + closing:
                    # Look for next opening bracket after the empty pair
                    open_pos = text.find(opening, open_pos + 2)
                    if open_pos == -1:
                        continue  # No more openings, try next bracket type

                # Find matching closing bracket
                depth = 0
                for i in range(open_pos, len(text)):
                    if text[i] == opening:
                        depth += 1
                    elif text[i] == closing:
                        depth -= 1
                        if depth == 0:
                            content = text[open_pos + 1:i]
                            # Extract wrapper prefix before the opening bracket
                            wrapper = text[:open_pos] if open_pos > 0 else None
                            return opening, closing, content, wrapper, None

        return None

    def _has_kv_separator_at_depth_zero(self, text: str, separator: str) -> bool:
        """
        Check if text contains a key-value separator at depth 0.

        Used to distinguish tuple elements {"a", {...}} from key-value pairs {a: {...}}.

        Args:
            text: Text to check
            separator: Separator to look for (e.g., ":")

        Returns:
            True if separator found at depth 0
        """
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(text):
            # Track strings
            if not in_string and char in ('"', "'", "`"):
                in_string = True
                string_char = char
                continue
            if in_string:
                if char == string_char and (i == 0 or text[i-1] != '\\'):
                    in_string = False
                    string_char = None
                continue

            # Track brackets outside strings
            if char in "({[":
                depth += 1
            elif char in ")}]":
                depth -= 1
            elif depth == 0 and text[i:].startswith(separator):
                return True

        return False

    def _extract_deepest_nested(
        self,
        text: str,
        opening: str,
        closing: str
    ) -> Optional[Tuple[str, str, str, Optional[str], str]]:
        """
        Extract the nested structure after the first comma in text.

        For tuple-like elements {"key", {...}}, this extracts the inner {...}.

        Args:
            text: Text to search (content between outer brackets, e.g., `"database", {...}`)
            opening: Opening bracket to search for
            closing: Closing bracket to match

        Returns:
            (opening, closing, content, wrapper, prefix) tuple or None
            prefix is the part before the nested structure (e.g., `"database", `)
        """
        # Find the first comma at depth 0 (outside strings and brackets)
        depth = 0
        in_string = False
        string_char = None
        comma_pos = -1

        for i, char in enumerate(text):
            # Track strings
            if not in_string and char in ('"', "'", "`"):
                in_string = True
                string_char = char
                continue
            if in_string:
                if char == string_char and (i == 0 or text[i-1] != '\\'):
                    in_string = False
                    string_char = None
                continue

            # Track brackets outside strings
            if char in "({[":
                depth += 1
            elif char in ")}]":
                depth -= 1
            elif char == ',' and depth == 0:
                comma_pos = i
                break  # Found first comma at depth 0

        if comma_pos == -1:
            return None  # No comma found - not a tuple

        # Now find opening bracket after the comma
        after_comma = text[comma_pos + 1:]
        open_pos_rel = after_comma.find(opening)
        if open_pos_rel == -1:
            return None  # No opening bracket after comma

        open_pos = comma_pos + 1 + open_pos_rel

        # Find matching closing bracket
        depth = 0
        for i in range(open_pos, len(text)):
            if text[i] == opening:
                depth += 1
            elif text[i] == closing:
                depth -= 1
                if depth == 0:
                    content = text[open_pos + 1:i]
                    # Prefix is everything before the opening bracket of nested structure
                    prefix = text[:open_pos]
                    return opening, closing, content, None, prefix

        return None

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

    def parse_nested(self, element: Element) -> Optional[List[Element]]:
        """
        Recursively parse nested content of an element.

        Args:
            element: Element with nested structure

        Returns:
            List of nested elements, or None if not nested
        """
        if not element.has_nested_structure:
            return None

        # Parse the nested content
        return self.parse(element.nested_content)
