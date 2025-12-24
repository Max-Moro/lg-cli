"""
Tree-sitter query definitions for C++ language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Comments
    "comments": """
    (comment) @comment
    """,

    # Preprocessor includes and imports
    "imports": """
    (preproc_include) @import

    (preproc_include
      path: (string_literal) @import_path)

    (preproc_include
      path: (system_lib_string) @import_path)

    (using_declaration) @import

    (namespace_alias_definition) @import
    """,
}
