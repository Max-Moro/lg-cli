"""
Kotlin language descriptor for literal optimization.

Defines patterns for Kotlin literals: strings, factory methods for collections.

Kotlin-specific patterns:
- String literals: single-line and multi-line raw strings
- String interpolation: ${expr} and $identifier
- Factory methods: listOf(), setOf(), mapOf() with 'to' operator
"""

from __future__ import annotations

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_string_opening(text: str) -> str:
    """Detect Kotlin string opening delimiter (regular or multi-line raw string)."""
    stripped = text.strip()
    if stripped.startswith('"""'):
        return '"""'
    if stripped.startswith('"'):
        return '"'
    if stripped.startswith("'"):
        return "'"
    return '"'


def _detect_string_closing(text: str) -> str:
    """Detect Kotlin string closing delimiter."""
    stripped = text.strip()
    if stripped.endswith('"""'):
        return '"""'
    if stripped.endswith('"'):
        return '"'
    if stripped.endswith("'"):
        return "'"
    return '"'


# ============= Kotlin literal patterns =============

# String literals (regular and multi-line raw strings)
KOTLIN_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["string_literal", "multiline_string_literal"],
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    # Kotlin supports both ${...} and $identifier interpolation
    interpolation_markers=[
        ("$", "{", "}"),  # ${expression}
        ("$", "", ""),     # $identifier
    ],
)

# Map.of equivalent: mapOf(k1 to v1, k2 to v2) - 'to' operator pairs
KOTLIN_MAP_OF = LiteralPattern(
    category=LiteralCategory.MAPPING,  # Changed from FACTORY_CALL to MAPPING
    tree_sitter_types=["call_expression"],
    wrapper_match=r"(mapOf|mutableMapOf|hashMapOf|linkedMapOf)$",
    opening="(",
    closing=")",
    separator=",",
    kv_separator=" to ",  # Kotlin uses 'to' operator for key-value pairs
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…" to "…"',  # Kotlin to operator in placeholder
    min_elements=1,
    comment_name="object",
    priority=20,  # Higher priority than generic factory
)

# Generic sequence factory: listOf(), setOf(), etc.
KOTLIN_LIST_OF = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["call_expression"],
    wrapper_match=r"(listOf|mutableListOf|arrayListOf)$",
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=15,
)

KOTLIN_SET_OF = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["call_expression"],
    wrapper_match=r"(setOf|mutableSetOf|hashSetOf|linkedSetOf)$",
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="set",
    priority=15,
)


def create_kotlin_descriptor() -> LanguageLiteralDescriptor:
    """Create Kotlin language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        patterns=[
            KOTLIN_MAP_OF,    # Highest priority - mapOf with 'to' pairs
            KOTLIN_LIST_OF,   # Mid priority - listOf variants
            KOTLIN_SET_OF,    # Mid priority - setOf variants
            KOTLIN_STRING,    # String literals
        ]
    )
