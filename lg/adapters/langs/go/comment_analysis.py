"""
Go-specific comment analyzer with position-based doc comment detection.

Provides language-specific implementation of CommentAnalyzer for Go.
In Go, doc comments are regular // comments that immediately precede
exported (public) declarations with no blank lines between them.
"""

from __future__ import annotations

from typing import List, Optional

from ...comment_style import CommentStyle
from ...context import ProcessingContext
from ...optimizations.comments import GroupingCommentAnalyzer
from ...tree_sitter_support import Node


class GoCommentAnalyzer(GroupingCommentAnalyzer):
    """
    Go-specific comment analyzer with position-based doc comment detection.

    In Go, a comment is considered a documentation comment if:
    1. It immediately precedes a top-level declaration (type, function, const, var)
    2. The declaration is exported (starts with uppercase letter)
    3. There are no blank lines between the comment and the declaration
    """

    def __init__(self, context: ProcessingContext, style: CommentStyle):
        """
        Initialize the Go comment analyzer.

        Args:
            context: Processing context with document and collector
            style: CommentStyle instance with comment markers
        """
        super().__init__(context.doc, style)
        # Store context for accessing shared collector
        self._context = context

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Check if a comment is a documentation comment.

        Go uses position-based detection: a comment is a doc comment if it
        immediately precedes an exported declaration with no blank lines.

        Args:
            node: AST node representing the comment
            text: Comment text content (unused, kept for interface compatibility)
            capture_name: Capture name from Tree-sitter query (unused)

        Returns:
            True if this is a documentation comment, False otherwise
        """
        # Ensure analysis is performed
        if not self._analyzed:
            self._analyze_all_comments()

        # Check if this comment's position is in the doc comments set
        position = (node.start_byte, node.end_byte)
        return position in self._doc_comment_positions

    def _analyze_all_comments(self) -> None:
        """
        Perform one-time analysis of all comments in the document.

        Groups consecutive comments and determines which groups are doc comments.
        """
        # Get all comment nodes
        comments = self.doc.query("comments")
        comment_nodes = [node for node, _ in comments]

        # Group consecutive comments
        self._comment_groups = self._group_consecutive_comments(comment_nodes)

        # Determine which groups are doc comments
        self._doc_comment_positions = set()

        for group in self._comment_groups:
            if self._is_doc_comment_group(group):
                # Mark all nodes in this group as doc comments
                for node in group:
                    position = (node.start_byte, node.end_byte)
                    self._doc_comment_positions.add(position)

        self._analyzed = True

    def _group_consecutive_comments(self, comment_nodes: List[Node]) -> List[List[Node]]:
        """
        Group consecutive comment nodes that form a logical block.

        Comments are consecutive if separated only by whitespace (no blank lines).

        Args:
            comment_nodes: List of comment nodes from Tree-sitter

        Returns:
            List of comment groups (each group is a list of nodes)
        """
        if not comment_nodes:
            return []

        groups = []
        current_group = [comment_nodes[0]]

        for i in range(1, len(comment_nodes)):
            prev_node = comment_nodes[i - 1]
            curr_node = comment_nodes[i]

            # Check for blank line between comments
            if self._has_blank_line_between(prev_node, curr_node):
                groups.append(current_group)
                current_group = [curr_node]
            else:
                # Also check that there's only whitespace between
                text_between = self.doc.text[prev_node.end_byte:curr_node.start_byte]
                if text_between.strip() == '':
                    current_group.append(curr_node)
                else:
                    groups.append(current_group)
                    current_group = [curr_node]

        if current_group:
            groups.append(current_group)

        return groups

    def _is_doc_comment_group(self, comment_group: List[Node]) -> bool:
        """
        Check if a comment group is a documentation comment.

        A group is a doc comment if it immediately precedes an exported declaration
        or package clause.

        Args:
            comment_group: List of consecutive comment nodes

        Returns:
            True if this group documents an exported declaration or package
        """
        if not comment_group:
            return False

        # First comment in group must start at beginning of line (not inline)
        # Inline comments (after code on same line) are not doc comments
        first_comment = comment_group[0]

        # Check if there's any non-whitespace before the comment on the same line
        line_start_byte = self.doc.text.rfind('\n', 0, first_comment.start_byte)
        if line_start_byte == -1:
            line_start_byte = 0
        else:
            line_start_byte += 1  # Skip the newline

        text_before_comment = self.doc.text[line_start_byte:first_comment.start_byte]
        if text_before_comment.strip():  # Non-whitespace found before comment
            return False

        last_comment = comment_group[-1]
        following_decl = self._find_following_declaration(last_comment)

        if not following_decl:
            return False

        # Doc comments must end BEFORE the line where declaration starts
        # This filters out edge cases where comment and decl are on same line
        comment_end_line = last_comment.end_point[0]
        decl_start_line = following_decl.start_point[0]
        if comment_end_line >= decl_start_line:
            return False

        # Package clause is always documented (package-level doc comment)
        if following_decl.type == 'package_clause':
            return True

        # Check if following declaration is public using ElementCollector
        return self._context.get_collector().is_public_declaration(following_decl)

    def _find_following_declaration(self, comment_node: Node) -> Optional[Node]:
        """
        Find the declaration that follows a comment node.

        Args:
            comment_node: The comment node to search from

        Returns:
            The following declaration node, or None if not found
        """
        parent = comment_node.parent
        if not parent:
            return None

        siblings = parent.children
        comment_idx = None

        for idx, sibling in enumerate(siblings):
            if sibling == comment_node:
                comment_idx = idx
                break

        if comment_idx is None:
            return None

        # Find next non-comment sibling
        for idx in range(comment_idx + 1, len(siblings)):
            sibling = siblings[idx]
            if sibling.type != 'comment':
                return sibling

        return None


__all__ = ["GoCommentAnalyzer"]
