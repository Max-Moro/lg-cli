"""Shared utilities for code profiles."""

from typing import Set
from lg.adapters.tree_sitter_support import Node


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


__all__ = ["is_inside_container"]
