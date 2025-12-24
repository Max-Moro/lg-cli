"""
Tree-sitter query definitions for Kotlin language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments (both single-line and multi-line)
    "comments": """
    (line_comment) @comment
    
    (block_comment) @comment
    """,

    # Import statements
    "imports": """
    (import) @import
    """,
}
