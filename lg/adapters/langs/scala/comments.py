"""
Scala-specific comment analyzer.
"""

from __future__ import annotations

from ...optimizations.comments import CommentAnalyzer


class ScalaCommentAnalyzer(CommentAnalyzer):
    """Scala-specific comment analyzer."""

    def get_comment_query(self) -> str:
        """Get Scala comment query."""
        return """
        (comment) @comment
        (block_comment) @comment
        """


__all__ = ["ScalaCommentAnalyzer"]
