"""
Profile classes for literal optimization patterns.

This module defines base profile classes for different literal types:
- StringProfile: For string literals
- SequenceProfile: For sequences (lists, arrays, vectors)
- MappingProfile: For mappings (dicts, maps, objects)

Profiles encapsulate the common attributes needed to describe how a specific
literal pattern should be recognized and optimized. These profiles will be
converted to LiteralPattern instances during initialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Union

from .categories import PlaceholderPosition


@dataclass
class StringProfile:
    """
    Profile for string literal patterns.

    Describes how to recognize and process string literals, including
    handling of interpolation, whitespace preservation, and placeholder
    positioning within the string content.
    """

    """Tree-sitter query to match this string pattern (S-expression format)."""
    query: str

    """
    Opening delimiter for the string.
    Can be a static string (e.g., double quote, single quote, triple quotes) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    opening: Union[str, Callable[[str], str]]

    """
    Closing delimiter for the string.
    Can be a static string (e.g., double quote, single quote, triple quotes) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    closing: Union[str, Callable[[str], str]]

    """Where to place the placeholder when trimming. Default: inline within the string."""
    placeholder_position: PlaceholderPosition = PlaceholderPosition.INLINE

    """Template for the placeholder text. Default: ellipsis character."""
    placeholder_template: str = "…"

    """
    Whether to preserve exact whitespace when trimming.
    Set to True for raw strings or strings where whitespace is semantically important.
    """
    preserve_whitespace: bool = False

    """
    List of interpolation marker tuples (prefix, opening, closing).
    Examples:
        - ("$", "{", "}") for JS/TS/Kotlin ${...}
        - ("$", "", "") for Kotlin/Scala $identifier
        - ("#", "{", "}") for Ruby #{...}
        - ("", "{", "}") for Rust/Python {...}
    Empty list means no interpolation (safe to cut anywhere).
    """
    interpolation_markers: List[tuple] = field(default_factory=list)

    """
    Optional callback to check if interpolation markers are active.
    Signature: (opening: str, content: str) -> bool
    Used for conditional activation (e.g., Python f-strings, Rust format strings).
    """
    interpolation_active: Optional[Callable[[str, str], bool]] = None

    """Priority for pattern matching. Higher values are checked first."""
    priority: int = 0

    """
    Optional custom name for comments about this pattern.
    If not set, defaults to the literal category name.
    """
    comment_name: Optional[str] = None


@dataclass
class SequenceProfile:
    """
    Profile for sequence literal patterns.

    Describes how to recognize and process sequence literals (arrays, lists,
    vectors, tuples, slices), including element separation, placeholder
    positioning, and minimum element preservation.
    """

    """Tree-sitter query to match this sequence pattern (S-expression format)."""
    query: str

    """
    Opening delimiter for the sequence.
    Can be a static string (e.g., bracket or paren) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    opening: Union[str, Callable[[str], str]]

    """
    Closing delimiter for the sequence.
    Can be a static string (e.g., bracket or paren) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    closing: Union[str, Callable[[str], str]]

    """Element separator string. Default: comma."""
    separator: str = ","

    """
    Where to place the placeholder when trimming.
    Default: end (before closing delimiter).
    """
    placeholder_position: PlaceholderPosition = PlaceholderPosition.END

    """Template for the placeholder text. Default: quoted ellipsis."""
    placeholder_template: str = '"…"'

    """Minimum number of elements to keep, even if over budget."""
    min_elements: int = 1

    """Priority for pattern matching. Higher values are checked first."""
    priority: int = 0

    """
    Optional custom name for comments about this pattern.
    If not set, defaults to the literal category name.
    """
    comment_name: Optional[str] = None

    """
    Whether this pattern requires AST-based element extraction.
    When True: uses tree-sitter node.children instead of text parsing.
    Useful for sequences without explicit separators (e.g., concatenated strings).
    """
    requires_ast_extraction: bool = False


@dataclass
class MappingProfile:
    """
    Profile for mapping literal patterns.

    Describes how to recognize and process mapping literals (dicts, maps,
    objects, hash maps), including key-value separation, element separation,
    and handling of typed structures where all keys must be preserved.
    """

    """Tree-sitter query to match this mapping pattern (S-expression format)."""
    query: str

    """
    Opening delimiter for the mapping.
    Can be a static string (e.g., brace) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    opening: Union[str, Callable[[str], str]]

    """
    Closing delimiter for the mapping.
    Can be a static string (e.g., brace) or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    closing: Union[str, Callable[[str], str]]

    """Element separator string. Default: comma."""
    separator: str = ","

    """Key-value separator string. Default: colon."""
    kv_separator: str = ":"

    """
    Where to place the placeholder when trimming.
    Default: middle (as a comment between elements).
    """
    placeholder_position: PlaceholderPosition = PlaceholderPosition.MIDDLE_COMMENT

    """Template for the placeholder text. Default: key-value pair with ellipsis."""
    placeholder_template: str = '"…": "…"'

    min_elements: int = 1
    """Minimum number of elements to keep, even if over budget."""

    """Priority for pattern matching. Higher values are checked first."""
    priority: int = 0

    """
    Optional custom name for comments about this pattern.
    If not set, defaults to the literal category name.
    """
    comment_name: Optional[str] = None

    """
    For typed structures: preserve all keys/fields at top level.
    When True: all top-level keys are kept, optimization applied to nested values.
    Useful for struct literals where field names must be preserved.
    """
    preserve_all_keys: bool = False


@dataclass
class FactoryProfile:
    """
    Profile for factory method/macro patterns.

    Describes factory calls like List.of(...), vec![...], mapOf(...).
    Factory methods are language-specific ways to create collections or other
    data structures through function/method calls or macros.
    """

    """Tree-sitter query to match this factory pattern (S-expression format)."""
    query: str

    """
    Regex pattern to match wrapper name (e.g., r"List\\.of$", r"^vec$").
    Used to distinguish between different factory methods when multiple patterns
    match the same tree-sitter node type.
    """
    wrapper_match: str

    """
    Opening delimiter for arguments.
    Can be a static string (e.g., "(", "![") or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    opening: Union[str, Callable[[str], str]]

    """
    Closing delimiter for arguments.
    Can be a static string (e.g., ")", "]") or a callable that
    dynamically determines the delimiter based on the matched text.
    """
    closing: Union[str, Callable[[str], str]]

    """Element separator string. Default: comma."""
    separator: str = ","

    """
    Where to place the placeholder when trimming.
    Default: middle (as a comment between elements).
    """
    placeholder_position: PlaceholderPosition = PlaceholderPosition.MIDDLE_COMMENT

    """Template for the placeholder text. Default: quoted ellipsis."""
    placeholder_template: str = '"…"'

    """Minimum number of elements to keep, even if over budget."""
    min_elements: int = 1

    """Priority for pattern matching. Higher values are checked first."""
    priority: int = 0

    """
    Optional custom name for comments about this pattern.
    If not set, defaults to the literal category name.
    """
    comment_name: Optional[str] = None

    """
    Group elements into tuples of this size (for Map.of pair semantics).
    Default 1 = no grouping. Set to 2 for Map.of(k1, v1, k2, v2).
    """
    tuple_size: int = 1

    """
    For factory methods that create mappings: key-value separator.
    Examples: " to " for Kotlin mapOf("k" to "v"), " -> " for Scala Map("k" -> "v").
    None for sequence factories.
    """
    kv_separator: Optional[str] = None


@dataclass
class LanguageSyntaxFlags:
    """
    Language-specific syntax flags for literal optimization.

    Defines universal syntax characteristics that affect how literals
    are parsed and formatted across different languages.
    """

    # Comment syntax
    single_line_comment: Optional[str] = None  # e.g., "//", "#"
    block_comment_open: Optional[str] = None   # e.g., "/*", '"""'
    block_comment_close: Optional[str] = None  # e.g., "*/", '"""'

    # String literal support
    supports_raw_strings: bool = False          # r"...", R"(...)"
    supports_template_strings: bool = False     # `...`
    supports_multiline_strings: bool = False    # """..."""

    # Factory method patterns
    factory_wrappers: List[str] = field(default_factory=list)  # ["List.of", "vec!"]

    # Special initialization patterns
    supports_block_init: bool = False           # Java double-brace, Rust HashMap chains
    supports_ast_sequences: bool = False        # Concatenated strings without separators
