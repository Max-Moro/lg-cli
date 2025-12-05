"""
C++ language descriptor for literal optimization v2.

Extends C with C++-specific raw string literals.

C++ specific patterns:
- Raw string literals: R"(...)" and R"delimiter(...)delimiter"
- Initializer lists: {...} for arrays, vectors, maps
"""

from __future__ import annotations

import re

from ..c.literals_v2 import C_INITIALIZER_LIST, C_CONCATENATED_STRING
from ..optimizations.literals_v2 import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_cpp_string_opening(text: str) -> str:
    """
    Detect C++ string opening delimiter.

    Handles regular strings, char literals, and raw strings.
    """
    stripped = text.strip()

    # Check for raw string: R"delimiter(..."
    match = re.match(r'^R"([^(]*)\(', stripped)
    if match:
        delimiter = match.group(1)
        return f'R"{delimiter}('

    # Regular strings and chars
    if stripped.startswith("'"):
        return "'"
    return '"'


def _detect_cpp_string_closing(text: str) -> str:
    """
    Detect C++ string closing delimiter.
    """
    stripped = text.strip()

    # Check for raw string ending: ...)delimiter"
    # Need to find the delimiter by parsing from start
    match = re.match(r'^R"([^(]*)\(', stripped)
    if match:
        delimiter = match.group(1)
        return f'){delimiter}"'

    # Regular strings and chars
    if stripped.endswith("'"):
        return "'"
    return '"'


# ============= C++ literal patterns =============

# String literals (includes raw strings)
CPP_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["string_literal", "char_literal", "raw_string_literal"],
    opening=_detect_cpp_string_opening,
    closing=_detect_cpp_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],  # C++ has no string interpolation
    preserve_whitespace=True,  # Raw strings preserve whitespace
)

def create_cpp_descriptor() -> LanguageLiteralDescriptor:
    """Create C++ language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        patterns=[
            CPP_STRING,  # C++ strings (includes raw strings)
            C_CONCATENATED_STRING,  # Concatenated strings as sequences
            C_INITIALIZER_LIST,  # Reuse C initializer lists
        ]
    )
