"""Universal delimiter detection for string literals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass
class DelimiterConfig:
    """Configuration for delimiter detection."""

    # String prefixes (e.g., ["f", "r", "b"] for Python)
    string_prefixes: List[str] = field(default_factory=list)

    # Triple quote styles
    triple_quote_styles: List[str] = field(default_factory=lambda: ['"""', "'''"])

    # Single quote styles
    single_quote_styles: List[str] = field(default_factory=lambda: ['"', "'"])

    # Raw string patterns: [(regex_pattern, closing_callback)]
    # For complex cases like Rust r#"..."#, C++ R"delimiter(...)delimiter"
    # Callback signature: (text: str, opening: str) -> str
    raw_string_patterns: List[Tuple[str, Callable[[str, str], str]]] = field(default_factory=list)

    # Default delimiter if detection fails
    default_delimiter: str = '"'


class DelimiterDetector:
    """Universal delimiter detector for string literals."""

    def __init__(self, config: DelimiterConfig):
        self.config = config

    def detect_opening(self, text: str) -> str:
        """
        Detect opening delimiter from string text.

        Args:
            text: Full string literal text

        Returns:
            Opening delimiter (e.g., '"', 'f"' + '""', 'r#"')
        """
        stripped = text.strip()

        # 1. Check raw string patterns (highest priority)
        for pattern, _ in self.config.raw_string_patterns:
            match = re.match(pattern, stripped)
            if match:
                return match.group(0)

        # 2. Extract prefix if present
        prefix = ""
        if self.config.string_prefixes:
            # Build regex for all allowed prefixes
            prefix_chars = ''.join(set(''.join(self.config.string_prefixes)))
            prefix_pattern = f"^([{prefix_chars}]{{0,2}})"
            match = re.match(prefix_pattern, stripped, re.IGNORECASE)
            if match:
                prefix = match.group(1)

        rest = stripped[len(prefix):]

        # 3. Check triple quotes (before single quotes)
        for triple in self.config.triple_quote_styles:
            if rest.startswith(triple):
                return f"{prefix}{triple}"

        # 4. Check single quotes
        for single in self.config.single_quote_styles:
            if rest.startswith(single):
                return f"{prefix}{single}"

        # 5. Fallback
        return self.config.default_delimiter

    def detect_closing(self, text: str) -> str:
        """
        Detect closing delimiter from string text.

        Args:
            text: Full string literal text

        Returns:
            Closing delimiter (e.g., '"', '"' + '""', '#"')
        """
        stripped = text.strip()

        # 1. Check raw string patterns
        for pattern, closing_callback in self.config.raw_string_patterns:
            match = re.match(pattern, stripped)
            if match:
                # Get opening that was matched
                opening = match.group(0)
                # Call callback to compute closing
                return closing_callback(stripped, opening)

        # 2. Check triple quotes
        for triple in self.config.triple_quote_styles:
            if stripped.endswith(triple):
                return triple

        # 3. Check single quotes
        for single in self.config.single_quote_styles:
            if stripped.endswith(single):
                return single

        # 4. Fallback
        return self.config.default_delimiter
