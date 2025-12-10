"""
Profile classes for literal optimization patterns.

This module defines base profile classes for different literal types:
- StringProfile: For string literals
- SequenceProfile: For sequences (lists, arrays, vectors)
- MappingProfile: For mappings (dicts, maps, objects)
- FactoryProfile: For factory methods/macros (List.of(), vec![...])
- BlockInitProfile: For imperative block initialization (Java double-brace, Rust HashMap)

Profiles encapsulate the common attributes needed to describe how a specific
literal pattern should be recognized and optimized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Union


class PlaceholderPosition(Enum):
    """Where to place the trimming placeholder."""
    END = "end"                     # Before closing: [..., "…"] // comment
    MIDDLE_COMMENT = "middle"       # As comment in middle: [..., /* … comment */, ]
    INLINE = "inline"               # Inside string: "text…" // comment
    NONE = "none"                   # No placeholder (silent trim)


@dataclass
class ParsedLiteral:
    """
    Result of parsing a literal from source code.

    Contains all information needed for trimming and formatting.
    Category is determined by the profile type (use isinstance checks).
    """
    # Original text and position
    original_text: str
    start_byte: int
    end_byte: int

    # Profile (StringProfile, SequenceProfile, MappingProfile, FactoryProfile, or BlockInitProfile)
    # Typed as object to avoid circular imports; use isinstance() to check type
    profile: object

    # Parsed boundaries
    opening: str
    closing: str
    content: str  # Content without opening/closing

    # Layout information
    is_multiline: bool
    base_indent: str = ""       # Indentation of the line where literal starts
    element_indent: str = ""    # Indentation for elements inside

    # For factory calls: the wrapper (e.g., "List.of", "vec!")
    wrapper: Optional[str] = None

    # Token count of original
    original_tokens: int = 0


@dataclass
class TrimResult:
    """
    Result of trimming a literal.

    Contains the trimmed text and metadata about what was removed.
    """
    # Final trimmed text (ready to replace original)
    trimmed_text: str

    # Metrics
    original_tokens: int
    trimmed_tokens: int
    saved_tokens: int

    # What was trimmed
    elements_kept: int
    elements_removed: int

    # Comment to add (if placeholder_position requires it)
    comment_text: Optional[str] = None
    comment_position: Optional[int] = None  # Byte offset for comment insertion

    @property
    def savings_ratio(self) -> float:
        """Calculate token savings ratio."""
        if self.trimmed_tokens == 0:
            return float('inf')
        return self.saved_tokens / self.trimmed_tokens


@dataclass
class LiteralProfile:
    """
    Base profile class for all literal pattern types.

    Encapsulates common attributes shared across different literal types:
    - How to recognize the literal pattern (query)
    - How to delimit it (opening/closing) - may be None for block-based literals
    - Where to place the trimming placeholder
    - Optional custom comment name
    """

    """Tree-sitter query to match this literal pattern (S-expression format)."""
    query: str

    """
    Opening delimiter for the literal.
    Can be a static string (e.g., quote, bracket, paren) or a callable that
    dynamically determines the delimiter based on the matched text.
    For block-based literals (BlockInitProfile), this can be None.
    """
    opening: Union[str, Callable[[str], str], None] = None

    """
    Closing delimiter for the literal.
    Can be a static string (e.g., quote, bracket, paren) or a callable that
    dynamically determines the delimiter based on the matched text.
    For block-based literals (BlockInitProfile), this can be None.
    """
    closing: Union[str, Callable[[str], str], None] = None

    """Where to place the placeholder when trimming."""
    placeholder_position: PlaceholderPosition = PlaceholderPosition.END

    """Template for the placeholder text."""
    placeholder_template: str = "…"

    """
    Optional custom name for comments about this pattern.
    If not set, defaults to the literal category name.
    """
    comment_name: Optional[str] = None


@dataclass
class StringProfile(LiteralProfile):
    """
    Profile for string literal patterns.

    Describes how to recognize and process string literals, including
    handling of interpolation, whitespace preservation, and placeholder
    positioning within the string content.
    """

    """Where to place the placeholder when trimming. Default: inline within the string."""
    placeholder_position: PlaceholderPosition = PlaceholderPosition.INLINE

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


@dataclass
class SequenceProfile(LiteralProfile):
    """
    Profile for sequence literal patterns.

    Describes how to recognize and process sequence literals (arrays, lists,
    vectors, tuples, slices), including element separation, placeholder
    positioning, and minimum element preservation.
    """

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

    """
    Whether this pattern requires AST-based element extraction.
    When True: uses tree-sitter node.children instead of text parsing.
    Useful for sequences without explicit separators (e.g., concatenated strings).
    """
    requires_ast_extraction: bool = False


@dataclass
class MappingProfile(LiteralProfile):
    """
    Profile for mapping literal patterns.

    Describes how to recognize and process mapping literals (dicts, maps,
    objects, hash maps), including key-value separation, element separation,
    and handling of typed structures where all keys must be preserved.
    """

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

    """Minimum number of elements to keep, even if over budget."""
    min_elements: int = 1

    """
    For typed structures: preserve all keys/fields at top level.
    When True: all top-level keys are kept, optimization applied to nested values.
    Useful for struct literals where field names must be preserved.
    """
    preserve_all_keys: bool = False

    """
    Regex pattern to match wrapper name (for factory-style mappings).
    Used to distinguish between different mapping factories when multiple patterns
    match the same tree-sitter node type.
    Examples: r"(mapOf|hashMapOf)$" for Kotlin, r"(Map|HashMap)$" for Scala.
    None for literal mappings (Python dict, JavaScript object).
    """
    wrapper_match: Optional[str] = None


@dataclass
class FactoryProfile(LiteralProfile):
    """
    Profile for factory method/macro patterns.

    Describes factory calls like List.of(...), vec![...], mapOf(...).
    Factory methods are language-specific ways to create collections or other
    data structures through function/method calls or macros.
    """

    """
    Regex pattern to match wrapper name (e.g., r"List\\.of$", r"^vec$").
    Used to distinguish between different factory methods when multiple patterns
    match the same tree-sitter node type.
    # Required in practice, empty string is invalid and will fail at runtime
    """
    wrapper_match: str = ""

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
class BlockInitProfile(LiteralProfile):
    """
    Profile for imperative block initialization patterns.

    Describes imperative initialization blocks like Java double-brace
    initialization and Rust HashMap initialization chains.
    These are sequences of statements that initialize data structures.
    """

    """
    Path to statements block within the node (e.g., "class_body/block").
    Defines how to navigate from matched node to the block containing statements.
    None means the matched node itself is the block.
    """
    block_selector: Optional[str] = None

    """
    Pattern to match repetitive statements to trim (e.g., "*/method_invocation").
    Defines which statements within the block should be optimized.
    """
    statement_pattern: Optional[str] = None

    """
    Where to place the placeholder when trimming.
    Default: middle (as a comment between statements).
    """
    placeholder_position: PlaceholderPosition = PlaceholderPosition.MIDDLE_COMMENT

    """Minimum number of statements to keep, even if over budget."""
    min_elements: int = 1


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
