"""
Tree-sitter query definitions for Python language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments and docstrings
    "comments": """
    (comment) @comment
    
    (expression_statement
      (string) @docstring)
    """,

    # Import statements
    "imports": """
    (import_statement) @import
      
    (import_from_statement) @import_from
    """,
}
