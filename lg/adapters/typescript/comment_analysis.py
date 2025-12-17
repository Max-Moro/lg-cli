from __future__ import annotations

from typing import ClassVar

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from ..tree_sitter_support import TreeSitterDocument, Node


class TypeScriptCommentAnalyzer(CommentAnalyzer):
    """
    TypeScript-specific comment analyzer with JSDoc support.

    Uses standard JSDoc style documentation (/** ... */).
    Inherits all behavior from base CommentAnalyzer.
    """

    # TypeScript uses C-style comments with JSDoc
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )


__all__ = ["TypeScriptCommentAnalyzer"]
