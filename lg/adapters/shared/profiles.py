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

    name: str
    """
    Profile name for metrics and placeholders.
    Examples: "class", "function", "method", "field", "variable".

    Used for:
    - Metrics: {language}.removed.{name}
    - Placeholder: "... {name} omitted ..."
    """

    query: str
    """
    Tree-sitter query for finding elements of this type.

    IMPORTANT: Must be single-pattern query. Capture name must be @element.

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

    parent_profile: Optional[str] = None
    """
    Name of parent profile for inheritance.

    When inheriting:
    - query is taken from parent (if not overridden)
    - additional_check is combined (parent AND child)
    - is_public is taken from child if specified, else from parent
    """


__all__ = ["ElementProfile"]
