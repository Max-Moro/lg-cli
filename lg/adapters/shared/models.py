"""
Data models for code elements.
Unified representation for both public API and function body optimizations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from lg.adapters.tree_sitter_support import Node
from .profiles import ElementProfile


@dataclass
class CodeElement:
    """
    Unified representation of a code element.

    Contains all information needed for both public API filtering
    and function body optimization.
    """

    # --- Identification ---

    profile: ElementProfile
    """The profile that matched this element."""

    node: Node
    """Tree-sitter node of the element definition."""

    name: Optional[str] = None
    """
    Name of this specific element in code (e.g., "MyClass", "process_data").

    Used for:
    - FunctionBodyConfig.except_patterns (regex filtering by function name)
    - Logging and debugging
    """

    # --- Public API status ---

    is_public: bool = True
    """
    Whether element is part of public API.

    Computed via profile.is_public callback.
    True by default (if profile.is_public is None).
    """

    # --- Function body info (only when profile.has_body=True) ---

    body_node: Optional[Node] = None
    """Body node of the function/method. None if no body or profile.has_body=False."""

    body_range: Optional[Tuple[int, int]] = None
    """
    Byte range for stripping: (start_byte, end_byte).

    Computed by collector, accounts for:
    - Protected content (docstrings) that should be preserved
    - For brace-languages: excludes opening '{' and closing '}'
    """

    docstring_node: Optional[Node] = None
    """Docstring node if found (for preservation when stripping)."""

    return_node: Optional[Node] = None
    """Return statement node at end of body (for preservation when trimming)."""

    decorators: List[Node] = field(default_factory=list)
    """List of decorator/annotation nodes attached to this element."""

    # --- Adjusted element boundaries ---

    element_range: Optional[Tuple[int, int]] = None
    """
    Adjusted byte range for the element (start_byte, end_byte).

    When set, overrides node boundaries. Used for:
    - Including trailing punctuation (semicolons, commas) in element range
    - Excluding leading noise not relevant to the element

    If None, boundaries are computed from node (and decorators for start).
    """

    # --- Computed properties ---

    @property
    def start_byte(self) -> int:
        """Start byte position of element (including decorators if any)."""
        if self.element_range is not None:
            return self.element_range[0]
        if self.decorators:
            return min(d.start_byte for d in self.decorators)
        return self.node.start_byte

    @property
    def end_byte(self) -> int:
        """End byte position of element (including trailing punctuation if adjusted)."""
        if self.element_range is not None:
            return self.element_range[1]
        return self.node.end_byte

    @property
    def full_range(self) -> Tuple[int, int]:
        """Full byte range including decorators."""
        return (self.start_byte, self.end_byte)


__all__ = ["CodeElement"]
