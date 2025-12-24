"""
Tree-sitter query definitions for Java language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments (both single-line and block comments)
    "comments": """
    (line_comment) @comment

    (block_comment) @comment
    """,

    # Import statements
    "imports": """
    (import_declaration) @import
    """,
}
