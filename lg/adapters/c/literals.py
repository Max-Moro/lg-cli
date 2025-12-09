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
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
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


# ============= C literal patterns =============

# String literals (interpreted strings)
C_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
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

# Concatenated strings: treat as a sequence where each child string is an element
# This allows keeping the first complete string and removing the rest
# Requires AST extraction since there's no explicit separator between strings
C_CONCATENATED_STRING = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
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

# Initializer lists: {...} for arrays and structs
# These can be numeric arrays or struct arrays
C_INITIALIZER_LIST = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
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
        _patterns=[
            C_STRING,
            C_CONCATENATED_STRING,
            C_INITIALIZER_LIST,
        ]
    )
