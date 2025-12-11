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

from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    SequenceProfile,
    LanguageSyntaxFlags,
)


def _detect_string_opening(text: str) -> str:
    """Detect C string opening delimiter."""
    stripped = text.strip()
    if stripped.startswith("'"):
        return "'"
    return '"'


def _detect_string_closing(text: str) -> str:
    """Detect C string closing delimiter."""
    stripped = text.strip()
    if stripped.endswith("'"):
        return "'"
    return '"'


# C literal profiles

# String profile for C string literals (interpreted strings)
C_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (char_literal) @lit
    ]
    """,
    opening=_detect_string_opening,
    closing=_detect_string_closing,
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
    min_elements=1,
    comment_name="literal string",
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
    min_elements=1,
    comment_name="array",
)


def create_c_descriptor() -> LanguageLiteralDescriptor:
    """Create C language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # Language syntax flags
        syntax=LanguageSyntaxFlags(
            single_line_comment="//",
            block_comment_open="/*",
            block_comment_close="*/",
            supports_raw_strings=False,          # C has no raw strings
            supports_template_strings=False,     # C has no template strings
            supports_multiline_strings=False,    # C has no multiline strings
            factory_wrappers=[],                 # C has no factory methods
            supports_block_init=False,           # C has no block init
            supports_ast_sequences=True,         # C has concatenated strings
        ),

        # String profiles
        string_profiles=[C_STRING_PROFILE],

        # Sequence profiles
        sequence_profiles=[
            C_CONCATENATED_STRING_PROFILE,
            C_INITIALIZER_LIST_PROFILE,
        ],
    )
