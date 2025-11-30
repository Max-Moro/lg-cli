"""
Tree-sitter query definitions for Go language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods (unified)
    "functions": """
    (function_declaration
      name: (identifier) @function_name
      parameters: (parameter_list) @function_params
      body: (block) @function_body) @function_definition

    (method_declaration
      receiver: (parameter_list) @method_receiver
      name: (field_identifier) @method_name
      parameters: (parameter_list) @method_params
      body: (block) @method_body) @method_definition

    (func_literal
      parameters: (parameter_list) @lambda_params
      body: (block) @lambda_body) @function_definition
    """,

    # Comments
    "comments": """
    (comment) @comment
    """,

    # Import declarations
    "imports": """
    (import_declaration) @import

    (import_spec
      path: (interpreted_string_literal) @import_path)

    (import_spec
      name: (package_identifier) @import_alias
      path: (interpreted_string_literal) @import_path)

    (import_spec
      name: (dot) @import_dot
      path: (interpreted_string_literal) @import_path)
    """,

    # Struct definitions (class equivalent)
    "classes": """
    (type_declaration
      (type_spec
        name: (type_identifier) @struct_name
        type: (struct_type
          (field_declaration_list) @struct_body)))
    """,

    # Interface definitions
    "interfaces": """
    (type_declaration
      (type_spec
        name: (type_identifier) @interface_name
        type: (interface_type
          (method_spec_list) @interface_body)))
    """,

    # Type definitions and aliases
    "type_aliases": """
    (type_declaration
      (type_spec
        name: (type_identifier) @type_name
        type: (_) @type_value))
    """,

    # Variable and constant declarations
    "variables": """
    (var_declaration
      (var_spec
        name: (identifier) @var_name
        type: (_)? @var_type
        value: (_)? @var_value))

    (const_declaration
      (const_spec
        name: (identifier) @const_name
        type: (_)? @const_type
        value: (_)? @const_value))

    (short_var_declaration
      left: (expression_list
        (identifier) @var_name)
      right: (_) @var_value)
    """,

    # Defer statements
    "defer_statements": """
    (defer_statement
      (call_expression) @deferred_call)
    """,

    # Go statements (goroutines)
    "go_statements": """
    (go_statement
      (call_expression) @goroutine_call)
    """,

    # Literals for trimming
    "literals": """
    (interpreted_string_literal) @string

    (raw_string_literal) @string

    (rune_literal) @string

    (int_literal) @number

    (float_literal) @number

    (imaginary_literal) @number

    (composite_literal) @array

    (slice_literal) @array

    (map_literal) @object
    """,

    # Package clause
    "packages": """
    (package_clause
      (package_identifier) @package_name)
    """,

    # Method receivers (for analysis)
    "receivers": """
    (method_declaration
      receiver: (parameter_list
        (parameter_declaration
          name: (identifier)? @receiver_name
          type: (_) @receiver_type)))
    """,
}
