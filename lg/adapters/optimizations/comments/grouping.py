"""
Grouping comment analyzer for languages with consecutive line comments.

Provides infrastructure for languages like Go and Rust where multiple
consecutive line comments form a single documentation block.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional, Set

from tree_sitter import Node

from .analyzer import CommentAnalyzer
from ...comment_style import CommentStyle
from ...tree_sitter_support import TreeSitterDocument


class GroupingCommentAnalyzer(CommentAnalyzer):
    """
    Comment analyzer with support for grouping consecutive line comments.

    Used by languages like Go and Rust where multiple consecutive line comments
    (e.g., // or ///) form a single documentation block.

    Subclasses must implement _analyze_all_comments() to populate _comment_groups.
    """

    def __init__(self, doc: TreeSitterDocument, style: CommentStyle):
        """
        Initialize the grouping analyzer.

        Args:
            doc: TreeSitterDocument instance to analyze
            style: CommentStyle instance with comment markers for this language
        """
        super().__init__(doc, style)
        self._comment_groups: Optional[List[List[Node]]] = None
        self._doc_comment_positions: Optional[Set[tuple[int, int]]] = None

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Check if a comment is a documentation comment.

        Ensures analysis is performed first, then delegates to base class
        for marker-based detection.

        Args:
            node: AST node representing the comment
            text: Comment text content
            capture_name: Capture name from Tree-sitter query

        Returns:
            True if this is a documentation comment, False otherwise
        """
        # Ensure analysis is performed (populates _comment_groups)
        if not self._analyzed:
            self._analyze_all_comments()

        # Use base class marker-based detection
        return super().is_documentation_comment(node, text, capture_name)

    def get_comment_group(self, node: Node) -> Optional[List[Node]]:
        """
        Get the comment group that contains the given comment node.

        Args:
            node: Comment node to find group for

        Returns:
            List of comment nodes in the same group, or None if not found
        """
        if self._comment_groups is None:
            return None

        # Use position-based comparison to avoid node identity issues
        target_position = (node.start_byte, node.end_byte)

        for group in self._comment_groups:
            for group_node in group:
                if (group_node.start_byte, group_node.end_byte) == target_position:
                    return group

        return None

    def _has_blank_line_between(self, node1: Node, node2: Node) -> bool:
        """
        Check if there's a blank line between two nodes.

        Args:
            node1: First node
            node2: Second node (must come after node1)

        Returns:
            True if there's a blank line between nodes
        """
        text_between = self.doc.text[node1.end_byte:node2.start_byte]
        return '\n\n' in text_between or '\r\n\r\n' in text_between

    @abstractmethod
    def _analyze_all_comments(self) -> None:
        """
        Perform one-time analysis of all comments in the document.

        Must populate self._comment_groups and self._doc_comment_positions,
        and set self._analyzed = True when complete.

        Subclasses implement language-specific grouping logic here.
        """
        pass


__all__ = ["GroupingCommentAnalyzer"]
