"""
Tree-sitter query definitions for Go language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments
    "comments": """
    (comment) @comment
    """,

    # Import declarations
    "imports": """
    (import_spec) @import
    """,
}
