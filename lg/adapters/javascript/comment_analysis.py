from __future__ import annotations

from typing import ClassVar

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from ..tree_sitter_support import TreeSitterDocument, Node


class JavaScriptCommentAnalyzer(CommentAnalyzer):
    """
    JavaScript-specific comment analyzer with JSDoc support.

    Uses standard JSDoc style documentation (/** ... */).
    Inherits all behavior from base CommentAnalyzer.
    """

    # JavaScript uses JSDoc style
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )


__all__ = ["JavaScriptCommentAnalyzer"]
