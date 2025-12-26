"""
C language descriptor for literal optimization.

Defines patterns for C literals: strings, arrays, initializer lists.

C-specific patterns:
- String literals: "", '' (with escapes)
- Concatenated strings: multiple string literals in sequence
- Initializer lists: {...} for arrays and structs
- No string interpolation (C has no interpolation)
"""

from __future__ import annotations

from ...optimizations.literals import *

C_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],  # No prefixes in C
    triple_quote_styles=[],  # No triple quotes
    single_quote_styles=['"', "'"],
    default_delimiter='"',
)

_c_detector = DelimiterDetector(C_DELIMITER_CONFIG)


# C literal profiles

# String profile for C string literals (interpreted strings)
C_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (char_literal) @lit
    ]
    """,
    opening=_c_detector.detect_opening,
    closing=_c_detector.detect_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
)

# Sequence profile for concatenated strings
# Treat as a sequence where each child string is an element
# Requires AST extraction since there's no explicit separator between strings
C_CONCATENATED_STRING_PROFILE = SequenceProfile(
    query="(concatenated_string) @lit",
    opening="",
    closing="",
    separator="",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template="…",
    comment_name="string",
    requires_ast_extraction=True,
)

# Sequence profile for initializer lists: {...} for arrays and structs
C_INITIALIZER_LIST_PROFILE = SequenceProfile(
    query="(initializer_list) @lit",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    comment_name="array",
)


def create_c_descriptor() -> LanguageLiteralDescriptor:
    """Create C language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            C_STRING_PROFILE,
            C_CONCATENATED_STRING_PROFILE,
            C_INITIALIZER_LIST_PROFILE,
        ]
    )
