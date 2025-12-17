from __future__ import annotations

from typing import ClassVar

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from ..tree_sitter_support import TreeSitterDocument, Node


class JavaCommentAnalyzer(CommentAnalyzer):
    """
    Java-specific comment analyzer with Javadoc support.

    Uses standard Javadoc style documentation (/** ... */).
    Inherits all behavior from base CommentAnalyzer.
    """

    # Java uses Javadoc style
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )


__all__ = ["JavaCommentAnalyzer"]
