"""
Scala language descriptor for literal optimization.

Defines patterns for Scala literals: strings, factory methods for collections.

Scala-specific patterns:
- String literals: single-line and multi-line, with interpolation support
- String interpolation: s"...", f"...", raw"..." with ${expr} and $identifier
- Factory methods: List(), Set(), Map() with arrow operator (->)
"""

from __future__ import annotations

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_string_opening(text: str) -> str:
    """Detect Scala string opening delimiter (with interpolation prefix)."""
    stripped = text.strip()
    # Check for triple-quoted strings first
    if stripped.startswith('s"""') or stripped.startswith('f"""') or stripped.startswith('raw"""'):
        return stripped[:4]  # s""", f""", raw"""
    if stripped.startswith('"""'):
        return '"""'
    # Check for interpolated strings
    if stripped.startswith('s"') or stripped.startswith('f"') or stripped.startswith('raw"'):
        return stripped[:2]
    if stripped.startswith('"'):
        return '"'
    if stripped.startswith("'"):
        return "'"
    return '"'


def _detect_string_closing(text: str) -> str:
    """Detect Scala string closing delimiter."""
    stripped = text.strip()
    if stripped.endswith('"""'):
        return '"""'
    if stripped.endswith('"'):
        return '"'
    if stripped.endswith("'"):
        return "'"
    return '"'


def _is_interpolated_string(opening: str, content: str) -> bool:
    """Check if string uses interpolation (s, f, or raw prefix)."""
    return opening.startswith(('s"', 'f"', 'raw"', 's"""', 'f"""', 'raw"""'))


# ============= Scala literal patterns =============

# String literals (regular and interpolated)
SCALA_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    query="""
    [
      (string) @lit
      (interpolated_string) @lit
      (interpolated_string_expression) @lit
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
    interpolation_active=_is_interpolated_string,
)

# Map factory with arrow operator: Map("key" -> "value")
SCALA_MAP = LiteralPattern(
    category=LiteralCategory.MAPPING,
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "Map" "mutableMap" "HashMap" "LinkedHashMap")
      arguments: (arguments)) @lit
    """,
    wrapper_match=r"(Map|mutableMap|HashMap|LinkedHashMap)$",
    opening="(",
    closing=")",
    separator=",",
    kv_separator=" -> ",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…" -> "…"',
    min_elements=1,
    comment_name="object",
    priority=20,
)

# List factory
SCALA_LIST = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "List" "Vector" "Seq" "Array")
      arguments: (arguments)) @lit
    """,
    wrapper_match=r"(List|Vector|Seq|Array)$",
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=15,
)

# Set factory
SCALA_SET = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    query="""
    (call_expression
      function: (identifier) @func_name
      (#any-of? @func_name "Set" "mutableSet" "HashSet" "LinkedHashSet")
      arguments: (arguments)) @lit
    """,
    wrapper_match=r"(Set|mutableSet|HashSet|LinkedHashSet)$",
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="set",
    priority=15,
)


def create_scala_descriptor() -> LanguageLiteralDescriptor:
    """Create Scala language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        _patterns=[
            SCALA_MAP,    # Highest priority - Map with arrow pairs
            SCALA_LIST,   # Mid priority - List variants
            SCALA_SET,    # Mid priority - Set variants
            SCALA_STRING, # String literals
        ]
    )
