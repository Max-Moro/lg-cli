"""
C++ initializer_list processor.

Handles C++ initializer_list nodes with special filtering to skip intermediate entries.
"""

from __future__ import annotations

from ...optimizations.literals import (
    StandardCollectionsProcessor,
    LiteralProfile,
    SequenceProfile,
)
from ...tree_sitter_support import Node, TreeSitterDocument


class CppInitializerListProcessor(StandardCollectionsProcessor):
    """
    Specialized processor for C++ initializer_list.

    C++ initializer_list creates AST nodes for:
    - Full collections: {{"x", 1}, {"y", 2}}
    - Map entries (pairs): {"key", {...}}
    - Elements: {"x", 1}

    All have the same node type "initializer_list", but entries should be skipped
    to avoid breaking structure during composition.

    This processor filters out entries and delegates actual processing
    to StandardCollectionsProcessor.
    """

    def can_handle(self, profile: LiteralProfile, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Check if this processor can handle the node.

        Handles ALL C++ initializer_list nodes.
        Entries will be filtered in process() to return None.

        Returns:
            True if can handle, False otherwise
        """
        # Only handle SequenceProfile with initializer_list type
        if not isinstance(profile, SequenceProfile):
            return False

        if node.type != "initializer_list":
            return False

        return True

    def process(self, node, doc, source_text, profile, budget):
        """
        Process C++ initializer_list node.

        Filters out entries and delegates to parent StandardCollectionsProcessor.

        Returns:
            TrimResult if optimization applied, None if entry or no optimization
        """
        # Skip entries - don't create any edit
        if self._is_entry(node):
            return None

        # Delegate to parent for actual processing
        return super().process(node, doc, source_text, profile, budget)

    def _is_entry(self, node: Node) -> bool:
        """
        Detect if node is an entry (pair/tuple) in a map structure.

        Entry detection heuristic:
        - Parent is also initializer_list
        - First significant child is a scalar (not initializer_list)

        Examples:
        - {"db", {...}} - entry (first child is string_literal)
        - {{"x", 1}, {"y", 2}} - collection (first child is initializer_list)
        - {"x", 1} - entry (first child is string_literal)

        Args:
            node: Node to check

        Returns:
            True if node is an entry, False otherwise
        """
        # Entry must have parent that is also initializer_list
        if not node.parent or node.parent.type != "initializer_list":
            return False

        # Get first significant child (skip punctuation)
        significant_children = [
            c for c in node.children
            if c.type not in ['{', '}', ',', '(', ')', '[', ']']
        ]

        if not significant_children:
            return False

        # If first child is scalar (not initializer_list), this is an entry
        first_child_type = significant_children[0].type
        return first_child_type != "initializer_list"
