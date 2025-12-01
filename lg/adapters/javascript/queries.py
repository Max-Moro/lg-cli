"""
Tree-sitter query definitions for JavaScript language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_declaration
      name: (identifier) @function_name
      parameters: (formal_parameters) @function_params
      body: (statement_block) @function_body) @function_definition

    (function_expression
      name: (identifier)? @function_name
      parameters: (formal_parameters) @function_params
      body: (statement_block) @function_body) @function_definition

    (arrow_function
      parameters: (_) @function_params
      body: (_) @function_body) @function_definition

    (method_definition
      name: (property_identifier) @method_name
      parameters: (formal_parameters) @method_params
      body: (statement_block) @method_body) @method_definition

    (method_definition
      name: (private_property_identifier) @method_name
      parameters: (formal_parameters) @method_params
      body: (statement_block) @method_body) @method_definition

    (generator_function
      name: (identifier) @function_name
      parameters: (formal_parameters) @function_params
      body: (statement_block) @function_body) @function_definition

    (generator_function_declaration
      name: (identifier) @function_name
      parameters: (formal_parameters) @function_params
      body: (statement_block) @function_body) @function_definition
    """,

    # Comments
    "comments": """
    (comment) @comment
    """,

    # Import and export statements
    "imports": """
    (import_statement) @import

    (import_statement
      source: (string) @import_source)
    """,

    # Export statements
    "exports": """
    (export_statement) @export

    (export_statement
      (function_declaration) @exported_function)

    (export_statement
      (class_declaration) @exported_class)

    (export_statement
      (lexical_declaration) @exported_variable)

    (export_statement
      (variable_declaration) @exported_variable)
    """,

    # Class definitions (ES6+)
    "classes": """
    (class_declaration
      name: (identifier) @class_name
      body: (class_body) @class_body)

    (class
      name: (identifier) @class_name
      body: (class_body) @class_body)
    """,

    # Variable declarations
    "variables": """
    (variable_declaration
      (variable_declarator
        name: (identifier) @variable_name
        value: (_)? @variable_value))

    (lexical_declaration
      (variable_declarator
        name: (identifier) @variable_name
        value: (_)? @variable_value))
    """,

    # Literals for trimming
    "literals": """
    (string) @string

    (template_string) @string

    (regex) @string

    (number) @number

    (array) @array

    (object) @object
    """,

    # Constructors
    "constructors": """
    (class_declaration
      body: (class_body
        (method_definition
          name: (property_identifier) @constructor_name
          (#eq? @constructor_name "constructor")
          parameters: (formal_parameters) @constructor_params
          body: (statement_block) @constructor_body)))

    (class
      body: (class_body
        (method_definition
          name: (property_identifier) @constructor_name
          (#eq? @constructor_name "constructor")
          parameters: (formal_parameters) @constructor_params
          body: (statement_block) @constructor_body)))
    """,

    # Getters and Setters
    "getters_setters": """
    (method_definition
      name: (property_identifier) @method_name
      (#match? @method_name "^(get|set)[A-Z]")
      body: (statement_block) @method_body) @getter_setter

    (pair
      key: (property_identifier) @property_name
      value: (function_expression
        body: (statement_block) @getter_body)
      (#match? @property_name "^get[A-Z]"))

    (pair
      key: (property_identifier) @property_name
      value: (function_expression
        parameters: (formal_parameters) @setter_params
        body: (statement_block) @setter_body)
      (#match? @property_name "^set[A-Z]"))
    """,

    # Class members (fields and methods)
    "class_members": """
    (class_body
      (field_definition
        property: (property_identifier) @field_name)) @field_definition

    (class_body
      (field_definition
        property: (private_property_identifier) @private_field_name)) @field_definition

    (class_body
      (method_definition
        name: (property_identifier) @method_name)) @method_definition

    (class_body
      (method_definition
        name: (private_property_identifier) @private_method_name)) @method_definition
    """,
}
