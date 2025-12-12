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

from ..optimizations.literals import *

GO_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],  # No prefixes in Go
    triple_quote_styles=[],  # No triple quotes
    single_quote_styles=['`', '"'],  # Backticks for raw strings
    default_delimiter='"',
)

_go_detector = DelimiterDetector(GO_DELIMITER_CONFIG)


# Go literal profiles

# String profile for Go string literals (interpreted and raw)
GO_STRING_PROFILE = StringProfile(
    query="""
    [
      (interpreted_string_literal) @lit
      (raw_string_literal) @lit
    ]
    """,
    opening=_go_detector.detect_opening,
    closing=_go_detector.detect_closing,
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
        profiles=[
            GO_STRING_PROFILE,
            GO_STRUCT_PROFILE,
            GO_MAP_PROFILE,
            GO_SLICE_PROFILE,
        ],
    )
