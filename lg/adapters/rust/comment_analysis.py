"""
Rust-specific comment analyzer with doc comment detection.

Provides language-specific implementation of CommentAnalyzer for Rust.
Rust has several types of documentation comments:
- /// - outer doc comment (documents following item)
- //! - inner doc comment (documents enclosing item/module)
- /** ... */ - outer block doc comment
- /*! ... */ - inner block doc comment
"""

from __future__ import annotations

from typing import ClassVar

from tree_sitter import Node

from ..optimizations.comment_analysis import CommentAnalyzer, CommentStyle


class RustCommentAnalyzer(CommentAnalyzer):
    """
    Rust-specific comment analyzer with doc comment detection.

    Rust has several doc comment types:
    - /// - outer doc comment (documents following item)
    - //! - inner doc comment (documents enclosing item/module)
    - /** - outer block doc comment
    - /*! - inner block doc comment
    """

    # Rust comment style
    STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("///", "")  # Primary doc marker
    )

    # All Rust doc comment markers
    DOC_MARKERS = ("///", "//!", "/**", "/*!")

    def is_documentation_comment(self, node: Node, text: str, capture_name: str = "") -> bool:
        """
        Determine if a comment is a documentation comment in Rust.

        Uses two strategies:
        1. Check if capture_name from Tree-sitter query is "docstring"
        2. Check if text starts with any Rust doc comment marker (///, //!, /**, /*!

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

        # Strategy 2: Text-based check for Rust doc markers
        stripped = text.strip()
        for marker in self.DOC_MARKERS:
            if stripped.startswith(marker):
                return True

        return False


__all__ = ["RustCommentAnalyzer"]
