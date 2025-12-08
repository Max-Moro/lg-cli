"""
Java language descriptor for literal optimization.

Defines patterns for Java literals: strings, text blocks, arrays, and factory methods.

Java-specific patterns:
- String literals: "..." and text blocks (Java 15+)
- Array initializers: { elem1, elem2, ... }
- Factory methods: List.of(), Set.of(), Map.of(), Map.ofEntries(), Arrays.asList(), Stream.of()

Note: Java has no string interpolation, so no interpolation_markers are needed.
"""

from __future__ import annotations

from ..optimizations.literals import (
    LiteralCategory,
    LiteralPattern,
    PlaceholderPosition,
    LanguageLiteralDescriptor,
)


def _detect_string_opening(text: str) -> str:
    """Detect Java string opening delimiter (regular or text block)."""
    stripped = text.strip()
    if stripped.startswith('"""'):
        return '"""'
    return '"'


def _detect_string_closing(text: str) -> str:
    """Detect Java string closing delimiter."""
    stripped = text.strip()
    if stripped.endswith('"""'):
        return '"""'
    return '"'


# ============= Java literal patterns =============

# String literals (regular and text blocks)
JAVA_STRING = LiteralPattern(
    category=LiteralCategory.STRING,
    tree_sitter_types=["string_literal"],
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],  # Java has no string interpolation
)

# Array initializers: { elem1, elem2, ... }
JAVA_ARRAY_INITIALIZER = LiteralPattern(
    category=LiteralCategory.SEQUENCE,
    tree_sitter_types=["array_initializer"],
    opening="{",
    closing="}",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

# Map.of(k1, v1, k2, v2) - pairs as separate arguments
# Must have higher priority than generic factory pattern
JAVA_MAP_OF = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    wrapper_match=r"Map\.of$",  # Match "Map.of" exactly (not Map.ofEntries)
    opening="(",
    closing=")",
    tuple_size=2,  # Group arguments into key-value pairs
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…", "…"',  # Placeholder is a pair
    min_elements=1,
    comment_name="map",
    priority=20,  # Higher than generic factory
)

# Map.ofEntries(Map.entry(...), ...) - each argument is a Map.entry() call
# Note: Map.entry is in factory_wrappers for nested detection but not a pattern itself
JAVA_MAP_OF_ENTRIES = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    wrapper_match=r"Map\.ofEntries$",
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='Map.entry("…", "…")',  # Placeholder is an entry
    min_elements=1,
    comment_name="map",
    priority=20,
)

# Generic sequence factory: List.of(), Set.of(), Stream.of(), Arrays.asList()
# Lower priority - catches any factory not matched above
JAVA_SEQUENCE_FACTORY = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    opening="(",
    closing=")",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=10,  # Lower than specific patterns
)

# Double-brace initialization: new HashMap<>() {{ put("k1", "v1"); put("k2", "v2"); }}
JAVA_DOUBLE_BRACE = LiteralPattern(
    category=LiteralCategory.BLOCK_INIT,
    tree_sitter_types=["object_creation_expression"],
    opening="",  # Not used for BLOCK_INIT
    closing="",  # Not used for BLOCK_INIT

    # BLOCK_INIT specific fields
    block_selector="class_body/block",  # Navigate to inner block
    statement_pattern="*/method_invocation",  # Match any method invocation (put, add, etc.)

    min_elements=1,
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    comment_name="double-brace init",
    priority=15,  # Medium priority
)


def create_java_descriptor() -> LanguageLiteralDescriptor:
    """Create Java language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        patterns=[
            JAVA_MAP_OF,           # High priority - pair-based Map.of
            JAVA_MAP_OF_ENTRIES,   # High priority - entry-based Map.ofEntries
            JAVA_DOUBLE_BRACE,     # Medium priority - double-brace initialization
            JAVA_SEQUENCE_FACTORY, # Catch-all for other factory methods
            JAVA_STRING,
            JAVA_ARRAY_INITIALIZER,
        ],
        nested_factory_wrappers=["Map.entry"],  # Nested wrappers for DFS detection
    )
