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
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
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


# ============= Go literal patterns =============

# String literals (interpreted and raw)
GO_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
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

# Composite literals: struct (typed, preserve fields)
# Struct literals: Type{field: value, ...}
# Match: type names (not starting with []" or "map[")
GO_COMPOSITE_STRUCT = LiteralPattern(
    category=LiteralCategory.MAPPING,
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
    priority=10,
)

# Composite literals: map (with key-value pairs)
# Map literals: map[K]V{key: value, ...}
GO_MAP = LiteralPattern(
    category=LiteralCategory.MAPPING,
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
    priority=6,
)

# Composite literals: slice (no key-value)
# Slice literals: []Type{elem1, elem2, ...}
GO_SLICE = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    query="""
    (composite_literal
      type: (slice_type) @slice_type
      body: (literal_value)) @lit
    """,
    opening="{",
    closing="}",
    wrapper_match=r"^\[\]",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="slice",
    priority=5,
)


def create_go_descriptor() -> LanguageLiteralDescriptor:
    """Create Go language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        patterns=[
            GO_COMPOSITE_STRUCT,       # Priority 10: Typed structs
            GO_MAP,                    # Priority 6: Maps with key-value
            GO_SLICE,                  # Priority 5: Slices
            GO_STRING,                 # Strings
        ]
    )
