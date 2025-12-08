"""
Core types and enums for literal optimization.

Defines universal literal categories, placeholder positions,
and data structures used throughout the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Union


class LiteralCategory(Enum):
    """Universal categories for literals across all languages."""
    STRING = "string"           # Any strings: single, multi, raw, template
    SEQUENCE = "sequence"       # Arrays, lists, vectors, tuples, slices
    MAPPING = "mapping"         # Dicts, maps, objects, hash maps
    FACTORY_CALL = "factory"    # List.of(), vec![], mapOf(), listOf()
    BLOCK_INIT = "block"        # { let mut m = ...; m }, lazy_static!


class PlaceholderPosition(Enum):
    """Where to place the trimming placeholder."""
    END = "end"                     # Before closing: [..., "…"] // comment
    MIDDLE_COMMENT = "middle"       # As comment in middle: [..., /* … comment */, ]
    INLINE = "inline"               # Inside string: "text…" // comment
    NONE = "none"                   # No placeholder (silent trim)


@dataclass
class LiteralPattern:
    """
    Describes how to recognize and process a specific literal pattern.

    Languages define their patterns declaratively, and the core
    optimizer uses them to classify and process literals.
    """
    category: LiteralCategory

    # Tree-sitter node types that match this pattern
    tree_sitter_types: List[str]

    # Opening/closing delimiters (string or callable for dynamic detection)
    # Callable signature: (text: str) -> str
    opening: Union[str, Callable[[str], str]]
    closing: Union[str, Callable[[str], str]]

    # Element separator (for sequences and mappings)
    separator: str = ","

    # Where to place placeholder when trimming
    placeholder_position: PlaceholderPosition = PlaceholderPosition.END

    # Placeholder text template (can include {count}, {tokens})
    placeholder_template: str = '"…"'

    # For mappings: key-value separator
    kv_separator: Optional[str] = None  # e.g., ":" for dicts, "->" for Scala maps

    # Minimum elements to keep (even if over budget)
    min_elements: int = 1

    # Whether this pattern preserves exact whitespace (raw strings)
    preserve_whitespace: bool = False

    # Priority for pattern matching (higher = checked first)
    priority: int = 0

    # Optional custom parser name (for special cases)
    custom_parser: Optional[str] = None

    # Comment name override (defaults to category.value)
    # Used for "literal {name}" comments
    comment_name: Optional[str] = None

    # String interpolation markers for safe truncation
    # List of (prefix, opening, closing) tuples:
    #   ("$", "{", "}") - JS/TS/Kotlin ${...}
    #   ("$", "", "")   - Kotlin/Scala $identifier
    #   ("#", "{", "}") - Ruby #{...}
    #   ("", "{", "}")  - Rust/Python {...}
    # Empty list means no interpolation (safe to cut anywhere)
    interpolation_markers: List[tuple] = field(default_factory=list)

    # Optional callback to check if interpolation markers are active for a specific string
    # Signature: (opening: str, content: str) -> bool
    # Used when markers need conditional activation (e.g., Python f-strings, Rust format strings)
    # None means markers are always active
    interpolation_active: Optional[Callable[[str, str], bool]] = None

    # For factory calls: regex pattern to match wrapper (e.g., r"List\.of")
    # Used to distinguish List.of from Map.of when both are method_invocation
    # None means no filtering (pattern matches any wrapper)
    wrapper_match: Optional[str] = None

    # Group elements into tuples of this size (for Map.of pair semantics)
    # Default 1 = no grouping. Set to 2 for Map.of(k1, v1, k2, v2)
    tuple_size: int = 1

    # Maximum character length for nested structures to stay inline (default: 60)
    nested_inline_threshold: int = 60

    # For typed structures: preserve all keys/fields at top level
    # When True: all top-level keys are kept, DFS applied to nested values
    # Useful for struct literals where field names must be preserved
    preserve_all_keys: bool = False

    # Whether this pattern requires AST-based element extraction
    # When True: uses tree-sitter node.children instead of text parsing
    # Useful for sequences without explicit separators (e.g., concatenated strings)
    requires_ast_extraction: bool = False

    # ========== BLOCK_INIT specific fields ==========
    # For imperative initialization blocks (Java double-brace, Rust HashMap blocks)

    # Path to statements block within the node (e.g., "class_body/block")
    block_selector: Optional[str] = None

    # Pattern to match repetitive statements to trim (e.g., "*/method_invocation")
    statement_pattern: Optional[str] = None

    def get_opening(self, text: str) -> str:
        """Get opening delimiter for given text."""
        if callable(self.opening):
            return self.opening(text)
        return self.opening

    def get_closing(self, text: str) -> str:
        """Get closing delimiter for given text."""
        if callable(self.closing):
            return self.closing(text)
        return self.closing


@dataclass
class ParsedLiteral:
    """
    Result of parsing a literal from source code.

    Contains all information needed for trimming and formatting.
    """
    # Original text and position
    original_text: str
    start_byte: int
    end_byte: int

    # Detected structure
    category: LiteralCategory
    pattern: LiteralPattern

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
