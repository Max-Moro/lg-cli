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
      body: (_) @function_body)
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
      name: (type_identifier) @interface_name)
    """,
    
    # Type definitions  
    "types": """
    (type_alias_declaration
      name: (type_identifier) @type_name
      value: (_) @type_value)
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
    
    (export_statement
      (function_declaration) @exported_function)
      
    (export_statement
      (class_declaration) @exported_class)
      
    (export_statement
      (interface_declaration) @exported_interface)
    """,
    
    # Visibility modifiers
    "visibility": """
    (method_definition
      (accessibility_modifier) @access_modifier
      name: (property_identifier) @method_name)
      
    (public_field_definition
      (accessibility_modifier) @access_modifier
      name: (property_identifier) @field_name)
      
    (class_declaration
      (accessibility_modifier) @access_modifier
      name: (type_identifier) @class_name)
    """,
    
    # Literals for trimming
    "literals": """
    (string) @string
    
    (template_string) @string
    
    (array) @array
    
    (object) @object
    
    (object_type) @object
    """,
    
    # Constructors and field-related methods
    "constructors": """
    (class_declaration
      body: (class_body
        (method_definition
          name: (property_identifier) @constructor_name
          (#eq? @constructor_name "constructor")
          body: (statement_block) @constructor_body)))
    """,
    
    "getters": """
    (class_declaration
      body: (class_body
        (method_definition
          (accessibility_modifier)? @access_modifier
          "get"
          name: (property_identifier) @getter_name
          body: (statement_block) @getter_body)))
    """,
    
    "setters": """
    (class_declaration
      body: (class_body
        (method_definition
          (accessibility_modifier)? @access_modifier
          "set"
          name: (property_identifier) @setter_name
          body: (statement_block) @setter_body)))
    """,
    
    "simple_getters_setters": """
    (method_definition
      name: (property_identifier) @method_name
      (#match? @method_name "^(get|set)[A-Z]")
      body: (statement_block) @method_body)
    """,
}
