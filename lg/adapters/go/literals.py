"""
Go language descriptor for literal optimization.

Defines patterns for Go literals: strings, slices, maps, structs.

Go-specific patterns:
- String literals: interpreted ("...") and raw (`...`)
- Composite literals: Type{elements} (slices, maps, structs)
  * Slices: []Type{elem1, elem2, ...}
  * Maps: map[K]V{key: value, ...}
  * Structs: Type{field: value, ...}

Note: Go has no string interpolation.
"""

from __future__ import annotations

from ..optimizations.literals import (
    PlaceholderPosition,
    LanguageLiteralDescriptor,
    StringProfile,
    MappingProfile,
    FactoryProfile,
)


def _detect_string_opening(text: str) -> str:
    """Detect Go string opening delimiter."""
    stripped = text.strip()
    if stripped.startswith('`'):
        return '`'
    return '"'


def _detect_string_closing(text: str) -> str:
    """Detect Go string closing delimiter."""
    stripped = text.strip()
    if stripped.endswith('`'):
        return '`'
    return '"'


# Go literal profiles

# String profile for Go string literals (interpreted and raw)
GO_STRING_PROFILE = StringProfile(
    query="""
    [
      (interpreted_string_literal) @lit
      (raw_string_literal) @lit
    ]
    """,
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
)

# Mapping profile for struct literals (typed, preserve fields)
# Struct literals: Type{field: value, ...}
# Match: type names (not starting with "map[")
GO_STRUCT_PROFILE = MappingProfile(
    query="""
    (composite_literal
      type: (type_identifier) @type_name
      (#not-match? @type_name "^map")
      body: (literal_value)) @lit
    """,
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    wrapper_match=r"^(?!map\[)(?!\[\]).*",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    preserve_all_keys=True,
    min_elements=1,
    comment_name="struct",
)

# Mapping profile for map literals
# Map literals: map[K]V{key: value, ...}
GO_MAP_PROFILE = MappingProfile(
    query="""
    (composite_literal
      type: (map_type) @map_type
      body: (literal_value)) @lit
    """,
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    wrapper_match=r"^map\[",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…": "…"',
    min_elements=1,
    comment_name="map",
)

# Factory profile for slice literals
# Slice literals: []Type{elem1, elem2, ...}
GO_SLICE_PROFILE = FactoryProfile(
    query="""
    (composite_literal
      type: (slice_type) @slice_type
      body: (literal_value)) @lit
    """,
    wrapper_match=r"^\[\]",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="slice",
)


def create_go_descriptor() -> LanguageLiteralDescriptor:
    """Create Go language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # String profiles
        string_profiles=[GO_STRING_PROFILE],

        # Mapping profiles
        mapping_profiles=[
            GO_STRUCT_PROFILE,  # Typed structs
            GO_MAP_PROFILE,     # Maps
        ],

        # Factory profiles
        factory_profiles=[GO_SLICE_PROFILE],  # Slices
    )
