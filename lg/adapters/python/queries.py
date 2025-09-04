"""
Tree-sitter query definitions for Python language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_definition
      name: (identifier) @function_name
      body: (block) @function_body)
    """,
    
    "methods": """
    (class_definition
      body: (block
        (function_definition
          name: (identifier) @method_name
          body: (block) @method_body)))
    """,
    
    # Comments and docstrings  
    "comments": """
    (comment) @comment
    
    (expression_statement
      (string) @docstring)
    """,
    
    # Import statements
    "imports": """
    (import_statement) @import_statement
      
    (import_from_statement) @import_from
    """,
    
    # Class definitions
    "classes": """
    (class_definition
      name: (identifier) @class_name
      body: (block) @class_body)
    """,
    
    # Variable assignments
    "assignments": """
    (assignment
      left: (identifier) @variable_name
      right: (_) @variable_value)
    """,
}
