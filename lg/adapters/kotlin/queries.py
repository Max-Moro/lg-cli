"""
Tree-sitter query definitions for Kotlin language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_declaration
      (identifier) @function_name
      (function_value_parameters) @function_params) @function_definition
    
    (function_declaration
      (function_body) @function_body)
    
    (lambda_literal) @function_definition
    """,
    
    # Comments (both single-line and multi-line)
    "comments": """
    (line_comment) @comment
    
    (block_comment) @comment
    """,
    
    # Import statements
    "imports": """
    (import) @import
    """,
    
    # Class definitions  
    "classes": """
    (class_declaration
      (identifier) @class_name
      (class_body)? @class_body)
    """,
    
    # Object declarations (Kotlin-specific)
    "objects": """
    (object_declaration
      (identifier) @object_name
      (class_body)? @object_body)
    """,
    
    # Properties (Kotlin val/var)
    "properties": """
    (property_declaration
      (variable_declaration
        (identifier) @property_name))
    """,
    
    # Literals for trimming
    "literals": """
    (string_literal) @string
    
    (multiline_string_literal) @string
    
    (number_literal) @number
    
    (float_literal) @number
    """,
    
    # Constructors and initializers
    "constructors": """
    (class_declaration
      (class_body
        (primary_constructor) @constructor))
    
    (class_declaration
      (class_body
        (secondary_constructor
          (function_value_parameters) @constructor_params
          (function_body)? @constructor_body) @constructor))
    
    (class_declaration
      (class_body
        (anonymous_initializer
          (statements) @init_body) @init_block))
    """,
    
    # Getters and Setters
    "getters_setters": """
    (property_declaration
      (getter
        (function_body)? @getter_body) @getter)
    
    (property_declaration
      (setter
        (function_value_parameters)? @setter_params
        (function_body)? @setter_body) @setter)
    """,
    
    # Annotations (Kotlin decorators)
    "annotations": """
    (modifiers
      (annotation) @annotation)
    """,
    
    # Visibility modifiers
    "visibility": """
    (modifiers
      (visibility_modifier) @visibility)
    """,
}

