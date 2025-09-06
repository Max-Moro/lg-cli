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
      body: (block) @function_body) @function_definition
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
    (import_statement) @import
      
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
    
    # Literals for trimming
    "literals": """
    (string) @string
    
    (list) @array
    
    (dictionary) @object
    
    (set) @array
    
    (tuple) @array
    """,
    
    # Constructors and field-related methods
    "constructors": """
    (class_definition
      body: (block
        (function_definition
          name: (identifier) @constructor_name
          (#eq? @constructor_name "__init__")
          body: (block) @constructor_body)))
    """,
    
    "properties": """
    (decorated_definition
      (decorator
        (identifier) @decorator_name
        (#eq? @decorator_name "property"))
      definition: (function_definition
        name: (identifier) @property_name
        body: (block) @property_body))
    """,
    
    "setters": """
    (decorated_definition
      (decorator
        (attribute
          object: (identifier) @property_base
          attribute: (identifier) @setter_attr
          (#eq? @setter_attr "setter")))
      definition: (function_definition
        name: (identifier) @setter_name
        body: (block) @setter_body))
    """,
    
    "simple_getters_setters": """
    (function_definition
      name: (identifier) @method_name
      (#match? @method_name "^(get_|set_)")
      body: (block) @method_body)
    """,
}
