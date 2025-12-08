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
    tree_sitter_types=["interpreted_string_literal", "raw_string_literal"],
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],  # Go has no string interpolation
)

# Composite literals: struct (typed, preserve fields)
# Struct literals: Type{field: value, ...}
# Match: type names (not starting with []" or "map[")
GO_COMPOSITE_STRUCT = LiteralPattern(
    category=LiteralCategory.MAPPING,
    tree_sitter_types=["composite_literal"],
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    wrapper_match=r"^(?!map\[)(?!\[\]).*",  # Not map, not slice
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    preserve_all_keys=True,  # Preserve all fields for typed structures
    min_elements=1,
    comment_name="struct",
    priority=10,  # Higher priority to match before generic collection
)

# Composite literals: map (with key-value pairs)
# Map literals: map[K]V{key: value, ...}
GO_MAP = LiteralPattern(
    category=LiteralCategory.MAPPING,
    tree_sitter_types=["composite_literal"],
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    wrapper_match=r"^map\[",  # Starts with map[
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…": "…"',
    min_elements=1,
    comment_name="map",
    priority=6,  # Between struct (10) and slice (5)
)

# Composite literals: slice (no key-value)
# Slice literals: []Type{elem1, elem2, ...}
GO_SLICE = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["composite_literal"],
    opening="{",
    closing="}",
    wrapper_match=r"^\[\]",  # Starts with []
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
