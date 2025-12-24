"""
Tree-sitter query definitions for JavaScript language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments
    "comments": """
    (comment) @comment
    """,

    # Import and export statements
    "imports": """
    (import_statement) @import

    (import_statement
      source: (string) @import_source)

    (export_statement
      source: (string) @export_from_source) @import
    """,
}
