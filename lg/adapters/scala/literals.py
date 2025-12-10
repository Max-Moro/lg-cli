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
    LanguageSyntaxFlags,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    MappingProfile,
    FactoryProfile,
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


# ============= Scala literal profiles (v2) =============

# String profile (regular and interpolated)
SCALA_STRING_PROFILE = StringProfile(
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
    min_elements=1,
    comment_name="object",
    priority=20,
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
    min_elements=1,
    comment_name="array",
    priority=15,
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
    min_elements=1,
    comment_name="set",
    priority=15,
)


def create_scala_descriptor() -> LanguageLiteralDescriptor:
    """Create Scala language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # String profiles
        # Language syntax flags
        syntax=LanguageSyntaxFlags(
            single_line_comment="//",
            block_comment_open="/*",
            block_comment_close="*/",
            supports_raw_strings=False,          # Scala has no raw strings (multiline """ is not raw)
            supports_template_strings=True,      # Scala has string interpolation s"", f"", raw""
            supports_multiline_strings=True,     # Scala has multiline strings """..."""
            factory_wrappers=["List", "Vector", "Seq", "Array", "Set", "mutableSet", "HashSet", "LinkedHashSet", "Map", "mutableMap", "HashMap", "LinkedHashMap"],
            supports_block_init=False,           # Scala has no block init
            supports_ast_sequences=False,        # Scala has no concatenated strings
        ),

        string_profiles=[SCALA_STRING_PROFILE],

        # Mapping profiles
        mapping_profiles=[SCALA_MAP_PROFILE],  # Map with arrow operator

        # Factory profiles
        factory_profiles=[
            SCALA_LIST_PROFILE,  # List variants
            SCALA_SET_PROFILE,   # Set variants
        ],
    )
