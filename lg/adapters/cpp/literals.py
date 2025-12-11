"""
C++ language descriptor for literal optimization.

Extends C with C++-specific raw string literals.

C++ specific patterns:
- Raw string literals: R"(...)" and R"delimiter(...)delimiter"
- Initializer lists: {...} for arrays, vectors, maps
"""

from __future__ import annotations

import re

from ..c.literals import C_INITIALIZER_LIST_PROFILE, C_CONCATENATED_STRING_PROFILE
from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
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


# C++ literal profiles

# String profile for C++ literals (includes raw strings)
CPP_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (char_literal) @lit
      (raw_string_literal) @lit
    ]
    """,
    opening=_detect_cpp_string_opening,
    closing=_detect_cpp_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
    preserve_whitespace=True,
)

def create_cpp_descriptor() -> LanguageLiteralDescriptor:
    """Create C++ language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # String profiles
        string_profiles=[CPP_STRING_PROFILE],

        # Sequence profiles
        sequence_profiles=[
            C_CONCATENATED_STRING_PROFILE,  # Reuse C concatenated strings
            C_INITIALIZER_LIST_PROFILE,      # Reuse C initializer lists
        ],
    )
