"""
Tree-sitter query definitions for C language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions
    "functions": """
    (function_definition
      declarator: (function_declarator
        declarator: (identifier) @function_name
        parameters: (parameter_list) @function_params)
      body: (compound_statement) @function_body) @function_definition

    (function_definition
      declarator: (pointer_declarator
        declarator: (function_declarator
          declarator: (identifier) @function_name
          parameters: (parameter_list) @function_params))
      body: (compound_statement) @function_body) @function_definition

    (function_definition
      declarator: (pointer_declarator
        declarator: (pointer_declarator
          declarator: (function_declarator
            declarator: (identifier) @function_name
            parameters: (parameter_list) @function_params)))
      body: (compound_statement) @function_body) @function_definition

    (function_definition
      declarator: (pointer_declarator
        declarator: (pointer_declarator
          declarator: (pointer_declarator
            declarator: (function_declarator
              declarator: (identifier) @function_name
              parameters: (parameter_list) @function_params))))
      body: (compound_statement) @function_body) @function_definition
    """,

    # Comments
    "comments": """
    (comment) @comment
    """,

    # Preprocessor includes (import equivalent)
    "imports": """
    (preproc_include) @import

    (preproc_include
      path: (string_literal) @import_path)

    (preproc_include
      path: (system_lib_string) @import_path)
    """,

    # Struct definitions (class equivalent in C)
    "classes": """
    (struct_specifier
      name: (type_identifier) @struct_name
      body: (field_declaration_list) @struct_body)

    (union_specifier
      name: (type_identifier) @union_name
      body: (field_declaration_list) @union_body)
    """,

    # Type definitions
    "typedefs": """
    (type_definition
      declarator: (type_identifier) @typedef_name)

    (type_definition
      type: (struct_specifier
        name: (type_identifier)? @struct_name)
      declarator: (type_identifier) @typedef_name)

    (type_definition
      type: (union_specifier
        name: (type_identifier)? @union_name)
      declarator: (type_identifier) @typedef_name)

    (type_definition
      type: (enum_specifier
        name: (type_identifier)? @enum_name)
      declarator: (type_identifier) @typedef_name)
    """,

    # Enum definitions
    "enums": """
    (enum_specifier
      name: (type_identifier) @enum_name
      body: (enumerator_list) @enum_body)
    """,

    # Function declarations (prototypes)
    "function_declarations": """
    (declaration
      declarator: (function_declarator
        declarator: (identifier) @function_name
        parameters: (parameter_list) @function_params)) @function_declaration

    (declaration
      declarator: (pointer_declarator
        declarator: (function_declarator
          declarator: (identifier) @function_name
          parameters: (parameter_list) @function_params))) @function_declaration

    (declaration
      declarator: (pointer_declarator
        declarator: (pointer_declarator
          declarator: (function_declarator
            declarator: (identifier) @function_name
            parameters: (parameter_list) @function_params)))) @function_declaration

    (declaration
      declarator: (pointer_declarator
        declarator: (pointer_declarator
          declarator: (pointer_declarator
            declarator: (function_declarator
              declarator: (identifier) @function_name
              parameters: (parameter_list) @function_params))))) @function_declaration
    """,

    # All declarations (function declarations and variable declarations)
    "declarations": """
    (declaration) @declaration
    """,

# Preprocessor defines (macros)
    "preprocessor": """
    (preproc_def
      name: (identifier) @macro_name
      value: (_)? @macro_value)

    (preproc_function_def
      name: (identifier) @macro_name
      parameters: (preproc_params) @macro_params
      value: (_)? @macro_value)

    (preproc_ifdef
      name: (identifier) @ifdef_name)

    (preproc_if
      condition: (_) @if_condition)

    (preproc_elif
      condition: (_) @elif_condition)
    """,
}
