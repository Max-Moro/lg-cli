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

from ..optimizations.literals import *

JAVA_DELIMITER_CONFIG = DelimiterConfig(
    string_prefixes=[],  # No prefixes in Java
    triple_quote_styles=['"""'],  # Text blocks (Java 15+)
    single_quote_styles=['"'],
    default_delimiter='"',
)

_java_detector = DelimiterDetector(JAVA_DELIMITER_CONFIG)


# Java literal profiles

# String profile (regular and text blocks)
JAVA_STRING_PROFILE = StringProfile(
    query="(string_literal) @lit",
    opening=_java_detector.detect_opening,
    closing=_java_detector.detect_closing,
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
)

# Block init profile for double-brace initialization: new HashMap<>() {{ put("k1", "v1"); put("k2", "v2"); }}
JAVA_DOUBLE_BRACE_PROFILE = BlockInitProfile(
    query="""
    (object_creation_expression
      (class_body
        (block))) @lit
    """,
    block_selector="class_body/block",
    statement_pattern="*/method_invocation",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    min_elements=1,
    comment_name="double-brace init",
)


def create_java_descriptor() -> LanguageLiteralDescriptor:
    """Create Java language descriptor for literal optimization."""
    return LanguageLiteralDescriptor(
        profiles=[
            JAVA_STRING_PROFILE,
            JAVA_ARRAY_PROFILE,
            JAVA_MAP_OF_PROFILE,
            JAVA_MAP_OF_ENTRIES_PROFILE,
            JAVA_LIST_SET_OF_PROFILE,
            JAVA_ARRAYS_ASLIST_PROFILE,
            JAVA_STREAM_OF_PROFILE,
            JAVA_DOUBLE_BRACE_PROFILE,
        ],

        nested_factory_wrappers=["Map.entry"],  # Nested wrappers for DFS detection
    )
