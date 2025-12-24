"""
Tree-sitter query definitions for TypeScript language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments
    "comments": """
    (comment) @comment
    """,

    # Import statements
    "imports": """
    (import_statement) @import
    """,
}
