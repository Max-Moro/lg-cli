"""
Go-specific comment analysis.

Provides logic to distinguish documentation comments from regular comments in Go.
In Go, doc comments are regular // comments that immediately precede exported declarations.
"""

from __future__ import annotations

from typing import Optional, List, Set

from .code_analysis import GoCodeAnalyzer
from ..tree_sitter_support import TreeSitterDocument, Node


class GoCommentAnalyzer:
    """
    Analyzes Go comments to determine if they are documentation comments.

    In Go, a comment is considered a documentation comment if:
    1. It immediately precedes a top-level declaration (type, function, const, var)
    2. The declaration is exported (starts with uppercase letter)
    3. There are no blank lines between the comment and the declaration
    """

    def __init__(self, doc: TreeSitterDocument, code_analyzer: GoCodeAnalyzer):
        """
        Initialize the comment analyzer.

        Args:
            doc: Parsed Tree-sitter document
            code_analyzer: Go code analyzer for determining element visibility
        """
        self.doc = doc
        self.code_analyzer = code_analyzer

        # Cache for analysis results
        self._comment_groups: Optional[List[List[Node]]] = None
        # Use (start_byte, end_byte) as key instead of node id, because Tree-sitter
        # creates new node objects on each query
        self._doc_comment_positions: Optional[Set[tuple[int, int]]] = None
        self._analyzed = False

    def is_documentation_comment(self, comment_node: Node) -> bool:
        """
        Check if a comment node is a documentation comment.

        Args:
            comment_node: Tree-sitter node for the comment

        Returns:
            True if this is a documentation comment (precedes exported declaration)
        """
        # Ensure analysis is performed
        if not self._analyzed:
            self._analyze_all_comments()

        # Check if this comment node's position is in the doc comments set
        position = (comment_node.start_byte, comment_node.end_byte)
        return position in self._doc_comment_positions

    def _analyze_all_comments(self) -> None:
        """
        Perform one-time analysis of all comments in the document.

        Groups consecutive comments and determines which groups are doc comments
        based on what declaration they precede.
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
                # Mark all nodes in this group as doc comments by their positions
                for node in group:
                    position = (node.start_byte, node.end_byte)
                    self._doc_comment_positions.add(position)

        self._analyzed = True

    def _group_consecutive_comments(self, comment_nodes: List[Node]) -> List[List[Node]]:
        """
        Group consecutive comment nodes that form a logical block.

        Comments are considered consecutive if they are only separated by whitespace
        (newlines, spaces) with no blank lines between them.

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

            # Get text between comments
            text_between = self.doc.text[prev_node.end_byte:curr_node.start_byte]

            # Check if there's only whitespace (no blank lines)
            # A blank line would have two consecutive newlines
            if '\n\n' not in text_between and text_between.strip() == '':
                # Continue current group
                current_group.append(curr_node)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [curr_node]

        # Add last group
        if current_group:
            groups.append(current_group)

        return groups

    def _is_doc_comment_group(self, comment_group: List[Node]) -> bool:
        """
        Check if a comment group is a documentation comment.

        A comment group is a doc comment if it immediately precedes
        an exported (public) top-level declaration.

        Args:
            comment_group: List of consecutive comment nodes

        Returns:
            True if this group documents an exported declaration
        """
        if not comment_group:
            return False

        # Get the last comment in the group
        last_comment = comment_group[-1]

        # Find what follows this comment group
        following_decl = self._find_following_declaration(last_comment)

        if not following_decl:
            return False

        # Check if it's a declaration type we care about
        decl_types = {
            'type_declaration',
            'function_declaration',
            'method_declaration',
            'var_declaration',
            'const_declaration'
        }

        if following_decl.type not in decl_types:
            return False

        # Analyze the declaration to check if it's exported
        try:
            elem_info = self.code_analyzer.analyze_element(following_decl)

            # In Go, doc comments are for exported elements
            # (though technically, unexported elements can have them too for internal docs)
            # For keep_doc policy, we'll consider only exported elements
            return elem_info.is_exported

        except Exception:
            # If analysis fails, assume it's not a doc comment
            return False

    def _find_following_declaration(self, comment_node: Node) -> Optional[Node]:
        """
        Find the declaration that follows a comment node.

        Looks for the next non-comment sibling after the given comment node.

        Args:
            comment_node: The comment node to search from

        Returns:
            The following declaration node, or None if not found
        """
        parent = comment_node.parent
        if not parent:
            return None

        siblings = parent.children

        # Find the index of the comment node
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

    def get_comment_group_for_node(self, comment_node: Node) -> Optional[List[Node]]:
        """
        Get the comment group that contains the given comment node.

        Args:
            comment_node: Comment node to find group for

        Returns:
            List of comment nodes in the same group, or None if not found
        """
        if not self._analyzed:
            self._analyze_all_comments()

        # Use position-based comparison to avoid node identity issues
        target_position = (comment_node.start_byte, comment_node.end_byte)

        for group in self._comment_groups:
            for node in group:
                if (node.start_byte, node.end_byte) == target_position:
                    return group

        return None


__all__ = ['GoCommentAnalyzer']
