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
from ..optimizations.literals import *
from .literals_component import CppInitializerListProcessor


def _cpp_raw_closing(opening: str) -> str:
    """
    Compute closing delimiter for C++ raw strings.

    C++ raw strings: R"(...)" or R"delimiter(...)delimiter"
    Closing is )delimiter" where delimiter matches opening.

    Args:
        opening: Matched opening delimiter (e.g., 'R"(', 'R"delim(')

    Returns:
        Closing delimiter (e.g., ')"', ')delim"')
    """
    # Extract delimiter name from opening: R"delimiter(" → "delimiter"
    match = re.match(r'^R"([^(]*)\(', opening)
    if match:
        delimiter = match.group(1)
        return f'){delimiter}"'
    # Fallback for malformed input
    return ')"'


CPP_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],
    triple_quote_styles=[],
    single_quote_styles=['"', "'"],
    raw_string_patterns=[
        (r'^R"([^(]*)\(', _cpp_raw_closing),  # R"delimiter(...)delimiter"
    ],
    default_delimiter='"',
)

_cpp_detector = DelimiterDetector(CPP_DELIMITER_CONFIG)


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
    opening=_cpp_detector.detect_opening,
    closing=_cpp_detector.detect_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
    preserve_whitespace=True,
)

def create_cpp_descriptor() -> LanguageLiteralDescriptor:
    """Create C++ language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            CPP_STRING_PROFILE,
            C_CONCATENATED_STRING_PROFILE,  # Reuse C concatenated strings
            C_INITIALIZER_LIST_PROFILE,      # Reuse C initializer lists
        ],
        custom_processor=CppInitializerListProcessor,
    )
