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
    StringProfile,
    SequenceProfile,
    FactoryProfile,
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


# ============= Java literal profiles (v2) =============

# String profile (regular and text blocks)
JAVA_STRING_PROFILE = StringProfile(
    query="(string_literal) @lit",
    opening=_detect_string_opening,
    closing=_detect_string_closing,
    placeholder_position=PlaceholderPosition.INLINE,
    placeholder_template="…",
    interpolation_markers=[],
)

# Array initializer sequence profile
JAVA_ARRAY_PROFILE = SequenceProfile(
    query="(array_initializer) @lit",
    opening="{",
    closing="}",
    separator=",",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
)

# Factory profiles

# Map.of(k1, v1, k2, v2) - pairs as separate arguments
JAVA_MAP_OF_PROFILE = FactoryProfile(
    query="""
    (method_invocation
      object: (identifier) @class_name
      (#eq? @class_name "Map")
      name: (identifier) @method_name
      (#eq? @method_name "of")
      arguments: (argument_list)) @lit
    """,
    wrapper_match=r"Map\.of$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…", "…"',
    min_elements=1,
    comment_name="map",
    priority=20,
    tuple_size=2,
)

# Map.ofEntries(Map.entry(...), ...) - each argument is a Map.entry() call
JAVA_MAP_OF_ENTRIES_PROFILE = FactoryProfile(
    query="""
    (method_invocation
      object: (identifier) @class_name
      (#eq? @class_name "Map")
      name: (identifier) @method_name
      (#eq? @method_name "ofEntries")
      arguments: (argument_list)) @lit
    """,
    wrapper_match=r"Map\.ofEntries$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='Map.entry("…", "…")',
    min_elements=1,
    comment_name="map",
    priority=20,
)

# List.of() and Set.of() - most common sequence factories
JAVA_LIST_SET_OF_PROFILE = FactoryProfile(
    query="""
    (method_invocation
      object: (identifier) @class_name
      (#any-of? @class_name "List" "Set")
      name: (identifier) @method_name
      (#any-of? @method_name "of" "copyOf")
      arguments: (argument_list)) @lit
    """,
    wrapper_match=r"(List|Set)\.(of|copyOf)$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=10,
)

# Arrays.asList() - legacy sequence factory
JAVA_ARRAYS_ASLIST_PROFILE = FactoryProfile(
    query="""
    (method_invocation
      object: (identifier) @class_name
      (#eq? @class_name "Arrays")
      name: (identifier) @method_name
      (#eq? @method_name "asList")
      arguments: (argument_list)) @lit
    """,
    wrapper_match=r"Arrays\.asList$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="array",
    priority=10,
)

# Stream.of() - stream sequence factory
JAVA_STREAM_OF_PROFILE = FactoryProfile(
    query="""
    (method_invocation
      object: (identifier) @class_name
      (#eq? @class_name "Stream")
      name: (identifier) @method_name
      (#eq? @method_name "of")
      arguments: (argument_list)) @lit
    """,
    wrapper_match=r"Stream\.of$",
    opening="(",
    closing=")",
    separator=",",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    placeholder_template='"…"',
    min_elements=1,
    comment_name="stream",
    priority=10,
)

# Double-brace initialization: new HashMap<>() {{ put("k1", "v1"); put("k2", "v2"); }}
JAVA_DOUBLE_BRACE = LiteralPattern(
    category=LiteralCategory.BLOCK_INIT,
    query="""
    (object_creation_expression
      (class_body
        (block))) @lit
    """,
    opening="",
    closing="",
    block_selector="class_body/block",
    statement_pattern="*/method_invocation",
    min_elements=1,
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    comment_name="double-brace init",
    priority=15,
)


def create_java_descriptor() -> LanguageLiteralDescriptor:
    """Create Java language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        # String profiles
        string_profiles=[JAVA_STRING_PROFILE],

        # Sequence profiles
        sequence_profiles=[JAVA_ARRAY_PROFILE],

        # Factory profiles
        factory_profiles=[
            JAVA_MAP_OF_PROFILE,           # High priority - pair-based Map.of
            JAVA_MAP_OF_ENTRIES_PROFILE,   # High priority - entry-based Map.ofEntries
            JAVA_LIST_SET_OF_PROFILE,      # Medium priority - List/Set.of()
            JAVA_ARRAYS_ASLIST_PROFILE,    # Medium priority - Arrays.asList()
            JAVA_STREAM_OF_PROFILE,        # Medium priority - Stream.of()
        ],

        # Legacy patterns (will be removed in later stages)
        _patterns=[
            JAVA_DOUBLE_BRACE,  # BLOCK_INIT - will migrate when BlockInitProfile is added
        ],

        nested_factory_wrappers=["Map.entry"],  # Nested wrappers for DFS detection
    )
