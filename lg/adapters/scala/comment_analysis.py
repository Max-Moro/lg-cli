from __future__ import annotations

from typing import ClassVar

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from ..tree_sitter_support import TreeSitterDocument, Node


class ScalaCommentAnalyzer(CommentAnalyzer):
    """
    Scala-specific comment analyzer with Scaladoc support.

    Uses Scaladoc style documentation (/** ... */), similar to Javadoc.
    Inherits all behavior from base CommentAnalyzer.
    """

    # Scala uses Scaladoc style (same as Javadoc format)
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )


__all__ = ["ScalaCommentAnalyzer"]
