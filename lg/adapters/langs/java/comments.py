"""
Java-specific comment analyzer.
"""

from __future__ import annotations

from ...comment_style import CommentStyle
from ...optimizations.comments import CommentAnalyzer
from ...tree_sitter_support import TreeSitterDocument


class JavaCommentAnalyzer(CommentAnalyzer):
    """Java-specific comment analyzer."""

    def get_comment_query(self) -> str:
        """Get Java comment query."""
        return """
        (line_comment) @comment
        (block_comment) @comment
        """


__all__ = ["JavaCommentAnalyzer"]
