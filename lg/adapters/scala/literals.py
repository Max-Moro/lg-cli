"""
Scala language descriptor for literal optimization.

Defines patterns for Scala literals: strings, factory methods for collections.

Scala-specific patterns:
- String literals: single-line and multi-line, with interpolation support
- String interpolation: s"...", f"...", raw"..." with ${expr} and $identifier
- Factory methods: List(), Set(), Map() with arrow operator (->)
"""

from __future__ import annotations

from ..optimizations.literals import *

SCALA_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=["s", "f", "raw"],  # Interpolation prefixes
    triple_quote_styles=['"""'],
    single_quote_styles=['"', "'"],
    default_delimiter='"',
)

_scala_detector = DelimiterDetector(SCALA_DELIMITER_CONFIG)


def _is_interpolated_string(opening: str) -> bool:
    """Check if string uses interpolation (s, f, or raw prefix)."""
    return opening.startswith(('s"', 'f"', 'raw"', 's"""', 'f"""', 'raw"""'))


# Scala literal profiles

# String profile (regular and interpolated)
SCALA_STRING_PROFILE = StringProfile(
    query="""
    [
      (string) @lit
      (interpolated_string) @lit
      (interpolated_string_expression) @lit
    ]
    """,
    opening=_scala_detector.detect_opening,
    closing=_scala_detector.detect_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[
        ("$", "{", "}"),
        ("$", "", ""),
    ],
    interpolation_active=_is_interpolated_string,
)

# Mapping profile for Map with arrow operator
SCALA_MAP_PROFILE = MappingProfile(
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "Map" "mutableMap" "HashMap" "LinkedHashMap")
      arguments: (arguments)) @lit
    """,
    opening="(",
    closing=")",
    separator=",",
    kv_separator=" -> ",
    wrapper_match=r"(Map|mutableMap|HashMap|LinkedHashMap)$",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…" -> "…"',
    comment_name="object",
)

# Factory profiles for List/Set
SCALA_LIST_PROFILE = FactoryProfile(
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "List" "Vector" "Seq" "Array")
      arguments: (arguments)) @lit
    """,
    wrapper_match=r"(List|Vector|Seq|Array)$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    comment_name="array",
)

SCALA_SET_PROFILE = FactoryProfile(
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "Set" "mutableSet" "HashSet" "LinkedHashSet")
      arguments: (arguments)) @lit
    """,
    wrapper_match=r"(Set|mutableSet|HashSet|LinkedHashSet)$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    comment_name="set",
)


def create_scala_descriptor() -> LanguageLiteralDescriptor:
    """Create Scala language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            SCALA_STRING_PROFILE,
            SCALA_MAP_PROFILE,
            SCALA_LIST_PROFILE,
            SCALA_SET_PROFILE,
        ]
    )
