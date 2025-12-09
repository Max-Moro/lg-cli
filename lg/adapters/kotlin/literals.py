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
    StringProfile,
    MappingProfile,
    FactoryProfile,
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


# ============= Kotlin literal profiles (v2) =============

# String profile (regular and multi-line raw strings with interpolation)
KOTLIN_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (multiline_string_literal) @lit
    ]
    """,
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[
        ("$", "{", "}"),
        ("$", "", ""),
    ],
)

# Mapping profile for mapOf with 'to' operator
KOTLIN_MAP_PROFILE = MappingProfile(
    query="""
    (call_expression
      (identifier) @func_name
      (#any-of? @func_name "mapOf" "mutableMapOf" "hashMapOf" "linkedMapOf")) @lit
    """,
    opening="(",
    closing=")",
    separator=",",
    kv_separator=" to ",
    wrapper_match=r"(mapOf|mutableMapOf|hashMapOf|linkedMapOf)$",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…" to "…"',
    min_elements=1,
    comment_name="object",
    priority=20,
)

# Factory profiles for list/set
KOTLIN_LIST_OF_PROFILE = FactoryProfile(
    query="""
    (call_expression
      (identifier) @func_name
      (#any-of? @func_name "listOf" "mutableListOf" "arrayListOf")) @lit
    """,
    wrapper_match=r"(listOf|mutableListOf|arrayListOf)$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=15,
)

KOTLIN_SET_OF_PROFILE = FactoryProfile(
    query="""
    (call_expression
      (identifier) @func_name
      (#any-of? @func_name "setOf" "mutableSetOf" "hashSetOf" "linkedSetOf")) @lit
    """,
    wrapper_match=r"(setOf|mutableSetOf|hashSetOf|linkedSetOf)$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="set",
    priority=15,
)


def create_kotlin_descriptor() -> LanguageLiteralDescriptor:
    """Create Kotlin language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # String profiles
        string_profiles=[KOTLIN_STRING_PROFILE],

        # Mapping profiles
        mapping_profiles=[KOTLIN_MAP_PROFILE],  # mapOf with 'to' operator

        # Factory profiles
        factory_profiles=[
            KOTLIN_LIST_OF_PROFILE,  # listOf variants
            KOTLIN_SET_OF_PROFILE,   # setOf variants
        ],
    )
