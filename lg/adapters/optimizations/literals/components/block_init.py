"""
Base class for imperative block initialization processors.

Provides common functionality for different initialization patterns:
- Java double-brace initialization
- Rust HashMap let-group initialization
"""

from __future__ import annotations

from .base import LiteralProcessor
from ....tree_sitter_support import TreeSitterDocument, Node


class BlockInitProcessorBase(LiteralProcessor):
    """
    Base class for block initialization processors.

    Handles formatting of block initialization patterns.
    Nested literals are automatically processed by the pipeline via add_replacement_composing_nested.
    """

    def __init__(
        self,
        tokenizer,
        comment_style: tuple[str, tuple[str, str]],
    ):
        """
        Initialize base processor.

        Args:
            tokenizer: Token counting service
            comment_style: Comment syntax (single_line, (block_open, block_close))
        """
        self.tokenizer = tokenizer
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

    def _matches_pattern(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """Check if node matches a pattern."""
        if pattern.startswith("*/"):
            target_pattern = pattern[2:]
            return self._matches_in_subtree(node, target_pattern, doc)

        if "[" in pattern:
            node_type, rest = pattern.split("[", 1)
            field_check = rest.rstrip("]")

            if node.type != node_type:
                return False

            if "=" in field_check:
                field_name, expected_value = field_check.split("=", 1)
                expected_value = expected_value.strip("'\"")

                field_node = node.child_by_field_name(field_name)
                if not field_node:
                    return False

                actual_value = doc.get_node_text(field_node)
                return actual_value == expected_value

            return False

        return node.type == pattern

    def _matches_in_subtree(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """Check if pattern matches anywhere in subtree."""
        if self._matches_pattern(node, pattern, doc):
            return True

        for child in node.children:
            if self._matches_in_subtree(child, pattern, doc):
                return True

        return False
