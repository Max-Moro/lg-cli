"""
C language descriptor for literal optimization v2.

Defines patterns for C literals: strings, arrays, initializer lists.

C-specific patterns:
- String literals: "", '' (with escapes)
- Concatenated strings: multiple string literals in sequence
- Initializer lists: {...} for arrays and structs
- No string interpolation (C has no interpolation)
"""

from __future__ import annotations

from ..optimizations.literals_v2 import (
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
    tree_sitter_types=["string_literal", "char_literal"],
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],  # C has no string interpolation
)

# Concatenated strings: treat as a sequence where each child string is an element
# This allows keeping the first complete string and removing the rest
# Requires AST extraction since there's no explicit separator between strings
C_CONCATENATED_STRING = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    tree_sitter_types=["concatenated_string"],
    opening="",  # No delimiters for concatenated strings
    closing="",
    separator="",  # Strings are just whitespace-separated
    placeholder_position=PlaceholderPosition.END,
    placeholder_template="…",
    min_elements=1,  # Keep at least the first string
    comment_name="literal string",
    requires_ast_extraction=True,  # Use AST to extract child string nodes
)

# Initializer lists: {...} for arrays and structs
# These can be numeric arrays or struct arrays
C_INITIALIZER_LIST = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    tree_sitter_types=["initializer_list"],
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
        patterns=[
            C_STRING,
            C_CONCATENATED_STRING,
            C_INITIALIZER_LIST,
        ]
    )
