"""
Tree-sitter query definitions for Rust language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments (including doc comments)
    "comments": """
    (line_comment) @comment

    (block_comment) @comment

    (line_comment
      (doc_comment)) @comment.doc

    (block_comment
      (doc_comment)) @comment.doc
    """,

    # Use declarations (imports)
    "imports": """
    (use_declaration) @import

    (extern_crate_declaration) @import
    """,
}
