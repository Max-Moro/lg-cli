"""
Kotlin language descriptor for literal optimization.

Defines patterns for Kotlin literals: strings, factory methods for collections.

Kotlin-specific patterns:
- String literals: single-line and multi-line raw strings
- String interpolation: ${expr} and $identifier
- Factory methods: listOf(), setOf(), mapOf() with 'to' operator
"""

from __future__ import annotations

from ...optimizations.literals import *

KOTLIN_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],  # No prefixes in Kotlin
    triple_quote_styles=['"""'],  # Only """ for multiline
    single_quote_styles=['"', "'"],
    default_delimiter='"',
)

_kotlin_detector = DelimiterDetector(KOTLIN_DELIMITER_CONFIG)


# Kotlin literal profiles

# String profile (regular and multi-line raw strings with interpolation)
KOTLIN_STRING_PROFILE = StringProfile(
    query="""
    [
      (string_literal) @lit
      (multiline_string_literal) @lit
    ]
    """,
    opening=_kotlin_detector.detect_opening,
    closing=_kotlin_detector.detect_closing,
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
    comment_name="object",
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
    comment_name="array",
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
    comment_name="set",
)


def create_kotlin_descriptor() -> LanguageLiteralDescriptor:
    """Create Kotlin language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            KOTLIN_STRING_PROFILE,
            KOTLIN_MAP_PROFILE,
            KOTLIN_LIST_OF_PROFILE,  # listOf variants
            KOTLIN_SET_OF_PROFILE,   # setOf variants
        ]
    )
