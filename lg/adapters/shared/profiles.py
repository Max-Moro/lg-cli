"""
Element profiles for declarative code element collection.
Defines what elements to find and how to determine their public API status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument


@dataclass
class ElementProfile:
    """
    Declarative description of a code element type.

    Profiles describe:
    - How to find elements (query)
    - How to determine if they're public (is_public callback)
    - Whether they have bodies (for function body optimization)
    """

    name: str = ""
    """
    Profile name for metrics and placeholders.
    Examples: "class", "function", "method", "field", "variable".

    When inherit_previous=True and name="", inherits name from previous profile.

    Used for:
    - Metrics: {language}.removed.{name}
    - Placeholder: "... {name} omitted ..."
    """

    query: str = ""
    """
    Tree-sitter query for finding elements of this type.

    IMPORTANT: Must be single-pattern query. Capture name must be @element.

    When inherit_previous=True and query="", inherits query from previous profile.

    Examples:
        "(class_definition) @element"
        "(function_definition) @element"
        "(method_definition) @element"
    """

    # --- Public API determination ---

    is_public: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Determines if element is part of public API.

    None = always public (default behavior).

    Single callback encapsulates all visibility/export logic:
    - Python: check _ and __ prefixes
    - Go: check first letter case
    - Java/Kotlin: check access modifiers
    - TypeScript top-level: check export keyword
    - TypeScript members: check private/protected modifiers

    Signature: (node: Node, doc: TreeSitterDocument) -> bool
    Returns: True if element is public, False if private
    """

    # --- Filtering ---

    additional_check: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Additional filtering when query cannot precisely filter elements.

    Examples:
    - Distinguish method from function: lambda n, d: is_inside_class(n)
    - Distinguish case class from class: lambda n, d: "case" in text[:50]

    Signature: (node: Node, doc: TreeSitterDocument) -> bool
    Returns: True if this node matches this profile type.
    """

    # --- Function body specific ---

    has_body: bool = False
    """
    True for elements with bodies (functions, methods).
    When True, collector will also extract body information.
    """

    body_query: Optional[str] = None
    """
    Query for extracting body node. Capture: @body.
    If None and has_body=True, collector searches for child named "block" or "body".
    """

    docstring_extractor: Optional[Callable[[Node, TreeSitterDocument], Optional[Node]]] = None
    """
    Extracts docstring node to preserve when stripping body.

    Only used when has_body=True.

    Signature: (body_node: Node, doc: TreeSitterDocument) -> Optional[Node]
    Returns: Docstring node if found, None otherwise.
    """

    body_resolver: Optional[Callable[[Node], Node]] = None
    """
    Resolve nested body structure to actual content node.

    Use when language AST has wrapper nodes around actual body content.
    Example: Kotlin function_body -> block (need to unwrap to inner block)

    Only used when has_body=True.

    Signature: (body_node: Node) -> Node
    Returns: Resolved body node for range computation.
    """

    body_range_computer: Optional[Callable[[Node, TreeSitterDocument], tuple[int, int]]] = None
    """
    Custom body range computation for non-standard AST structures.

    Use when element has special body structure that standard logic can't handle.
    Example: Kotlin lambda_literal has inline body without separate block node.

    Only used when has_body=True.

    Signature: (element_node: Node, doc: TreeSitterDocument) -> tuple[start_byte, end_byte]
    Returns: Byte range for strippable body content.
    """

    # --- Inheritance ---

    inherit_previous: bool = False
    """
    Inherit fields from previous profile in the list.

    When True, fields are inherited as follows:
    - name: inherits if current is "" (empty string)
    - query: inherits if current is "" (empty string)
    - is_public: inherits if current is None
    - additional_check: inherits if current is None (NO combining via AND)
    - has_body: inherits True from parent (current True always takes priority)
    - body_query: inherits if current is None
    - docstring_extractor: inherits if current is None
    - body_resolver: inherits if current is None
    - body_range_computer: inherits if current is None

    Example usage:
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_top_level,
            has_body=True,
            docstring_extractor=_find_docstring,
        ),
        ElementProfile(
            additional_check=lambda n, d: is_inside_class(n),
            inherit_previous=True,  # Inherits name, query, is_public, has_body, docstring_extractor
        ),
    """


__all__ = ["ElementProfile"]
