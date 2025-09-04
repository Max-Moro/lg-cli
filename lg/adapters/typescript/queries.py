"""
Tree-sitter query definitions for TypeScript language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_declaration
      name: (identifier) @function_name
      body: (statement_block) @function_body)
      
    (method_definition
      name: (property_identifier) @method_name  
      body: (statement_block) @method_body)
      
    (arrow_function
      body: (_) @arrow_function_body)
    """,
    
    "methods": """
    (class_declaration
      body: (class_body
        (method_definition
          name: (property_identifier) @method_name
          body: (statement_block) @method_body)))
    """,
    
    # Comments
    "comments": """
    (comment) @comment
    """,
    
    # Import statements
    "imports": """
    (import_statement) @import
    """,
    
    # Class definitions  
    "classes": """
    (class_declaration
      name: (type_identifier) @class_name
      body: (class_body) @class_body)
    """,
    
    # Interface definitions
    "interfaces": """
    (interface_declaration
      name: (type_identifier) @interface_name
      body: (object_type) @interface_body)
    """,
    
    # Variable declarations
    "variables": """
    (variable_declaration
      (variable_declarator
        name: (identifier) @variable_name
        value: (_)? @variable_value))
    """,
    
    # Export statements
    "exports": """
    (export_statement) @export
    """,
}
