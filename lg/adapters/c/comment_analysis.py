"""
C/C++ specific comment analyzer with Doxygen style detection.

Provides language-specific implementation of CommentAnalyzer for C/C++.
Supports Doxygen documentation markers (/** and ///).
"""

from __future__ import annotations

from typing import ClassVar

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from ..tree_sitter_support import TreeSitterDocument, Node


class CStyleCommentAnalyzer(CommentAnalyzer):
    """
    C/C++ specific comment analyzer with Doxygen style detection.

    Supports Doxygen documentation markers:
    - /** - block doc comment
    - /// - line doc comment
    """

    # C-style comment style with explicit Doxygen markers
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )

    # Doxygen doc comment markers
    DOC_MARKERS = ("/**", "///")

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Determine if a comment is a Doxygen documentation comment.

        Checks for Doxygen markers: /** and ///

        Args:
            node: AST node representing the comment
            text: Comment text content
            capture_name: Capture name from Tree-sitter query (optional)

        Returns:
            True if the comment is a documentation comment, False otherwise
        """
        # Strategy 1: Tree-sitter capture name
        if capture_name in ("docstring", "comment.doc"):
            return True

        # Strategy 2: Text-based check for Doxygen markers
        stripped = text.strip()
        for marker in self.DOC_MARKERS:
            if stripped.startswith(marker):
                return True

        return False


__all__ = ["CStyleCommentAnalyzer"]
