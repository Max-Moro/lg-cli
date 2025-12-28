"""Shared utilities for code profiles."""

from typing import Optional, Set, Tuple
from lg.adapters.tree_sitter_support import Node, TreeSitterDocument


def is_inside_container(
    node: Node,
    container_types: Set[str],
    boundary_types: Set[str] | None = None
) -> bool:
    """
    Check if node is inside any of the specified container types.

    Args:
        node: Tree-sitter node to check
        container_types: Node types that count as "inside" (e.g., {"class_definition", "class_body"})
        boundary_types: Node types that stop the search (e.g., {"module", "program"}).
                        If None, uses {"module", "program", "source_file", "translation_unit"}

    Returns:
        True if node is inside any container type
    """
    if boundary_types is None:
        boundary_types = {"module", "program", "source_file", "translation_unit"}

    current = node.parent
    while current:
        if current.type in container_types:
            return True
        if current.type in boundary_types:
            return False
        current = current.parent
    return False


def compute_element_range_with_trailing(
    node: Node,
    element_type: str,
    doc: TreeSitterDocument,
    *,
    element_types: Set[str],
    trailing_chars: Set[str],
) -> Optional[Tuple[int, int]]:
    """
    Compute adjusted element range to include trailing punctuation.

    Generic helper for languages where elements like fields or variables
    need to include trailing semicolons or commas in their range.

    Args:
        node: Element node
        element_type: Type of element (from profile.name)
        doc: Tree-sitter document
        element_types: Set of element types to process (e.g., {"field", "variable"})
        trailing_chars: Set of trailing characters to include (e.g., {";"} or {","})

    Returns:
        Tuple (start_byte, end_byte) if range should be adjusted, None otherwise.
    """
    # Only process specified element types
    if element_type not in element_types:
        return None

    # Check if there's trailing punctuation right after this node
    parent = node.parent
    if not parent:
        return None

    # Find position of this node among siblings
    siblings = parent.children
    node_index = None
    for i, sibling in enumerate(siblings):
        if sibling == node:
            node_index = i
            break

    if node_index is None:
        return None

    # Check if next sibling is one of the trailing characters
    if node_index + 1 < len(siblings):
        next_sibling = siblings[node_index + 1]
        sibling_text = doc.get_node_text(next_sibling).strip()
        if next_sibling.type in trailing_chars or sibling_text in trailing_chars:
            return node.start_byte, next_sibling.end_byte

    return None


__all__ = ["is_inside_container", "compute_element_range_with_trailing"]
