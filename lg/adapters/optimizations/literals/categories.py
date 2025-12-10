"""
Core types and enums for literal optimization.

Defines universal literal categories, placeholder positions,
and data structures used throughout the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    category: object  # LiteralCategory - typed as object to avoid circular imports
    # Profile (StringProfile, SequenceProfile, MappingProfile, FactoryProfile, or BlockInitProfile)
    profile: object  # Typed as object to avoid circular imports; use hasattr() to check attributes

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
