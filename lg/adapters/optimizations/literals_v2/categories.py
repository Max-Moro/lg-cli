"""
Core types and enums for literal optimization v2.

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
