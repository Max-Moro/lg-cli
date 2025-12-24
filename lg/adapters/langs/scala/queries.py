"""
Tree-sitter query definitions for Scala language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments
    "comments": """
    (comment) @comment

    (block_comment) @comment
    """,

    # Import statements
    "imports": """
    (import_declaration) @import

    (import_declaration
      path: (_) @import_path)
    """,
}
