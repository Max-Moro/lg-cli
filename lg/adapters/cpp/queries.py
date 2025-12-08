"""
Tree-sitter query definitions for C++ language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_definition
      declarator: (function_declarator
        declarator: (identifier) @function_name
        parameters: (parameter_list) @function_params)
      body: (compound_statement) @function_body) @function_definition

    (function_definition
      declarator: (function_declarator
        declarator: (qualified_identifier
          name: (identifier) @function_name)
        parameters: (parameter_list) @function_params)
      body: (compound_statement) @function_body) @function_definition

    (function_definition
      declarator: (pointer_declarator
        declarator: (function_declarator
          declarator: (identifier) @function_name
          parameters: (parameter_list) @function_params))
      body: (compound_statement) @function_body) @function_definition

    (lambda_expression
      declarator: (abstract_function_declarator
        parameters: (parameter_list) @lambda_params)
      body: (compound_statement) @lambda_body) @function_definition
    """,

    # Class/struct methods (member functions)
    "class_methods": """
    (field_declaration_list
      (function_definition
        declarator: (function_declarator
          declarator: (field_identifier) @function_name
          parameters: (parameter_list) @function_params)
        body: (compound_statement) @function_body) @function_definition)

    (field_declaration_list
      (function_definition
        declarator: (function_declarator
          declarator: (qualified_identifier
            name: (field_identifier) @function_name)
          parameters: (parameter_list) @function_params)
        body: (compound_statement) @function_body) @function_definition)

    (field_declaration_list
      (function_definition
        declarator: (pointer_declarator
          declarator: (function_declarator
            declarator: (field_identifier) @function_name
            parameters: (parameter_list) @function_params))
        body: (compound_statement) @function_body) @function_definition)
    """,

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

    # Class and struct definitions
    "classes": """
    (class_specifier
      name: (type_identifier) @class_name
      body: (field_declaration_list) @class_body)

    (struct_specifier
      name: (type_identifier) @struct_name
      body: (field_declaration_list) @struct_body)

    (union_specifier
      name: (type_identifier) @union_name
      body: (field_declaration_list) @union_body)
    """,

    # Template definitions
    "templates": """
    (template_declaration
      parameters: (template_parameter_list) @template_params
      (class_specifier
        name: (type_identifier) @class_name))

    (template_declaration
      parameters: (template_parameter_list) @template_params
      (struct_specifier
        name: (type_identifier) @struct_name))

    (template_declaration
      parameters: (template_parameter_list) @template_params
      (function_definition
        declarator: (function_declarator
          declarator: (identifier) @function_name)))
    """,

    # Namespace definitions
    "namespaces": """
    (namespace_definition
      (namespace_identifier) @namespace_name
      (declaration_list) @namespace_body)
    """,

    # Type definitions
    "typedefs": """
    (type_definition
      declarator: (type_identifier) @typedef_name)

    (alias_declaration
      name: (type_identifier) @alias_name
      type: (_) @alias_type)
    """,

    # Enum definitions
    "enums": """
    (enum_specifier
      name: (type_identifier) @enum_name
      body: (enumerator_list) @enum_body)
    """,

    # Class fields (member variables)
    "class_fields": """
    (field_declaration_list
      (field_declaration) @field_declaration)
    """,

    # Struct definitions (for collecting structs in anonymous namespaces)
    "structs": """
    (struct_specifier
      name: (type_identifier) @struct_name
      body: (field_declaration_list) @struct_body)
    """,

    # Constructors and destructors
    "constructors": """
    (function_definition
      declarator: (function_declarator
        declarator: (identifier) @constructor_name)
      body: (compound_statement) @constructor_body
      (#match? @constructor_name "^[A-Z]")) @constructor

    (function_definition
      declarator: (function_declarator
        declarator: (destructor_name) @destructor_name)
      body: (compound_statement) @destructor_body) @destructor
    """,

    # Visibility modifiers
    "visibility": """
    (access_specifier
      "public") @visibility.public

    (access_specifier
      "private") @visibility.private

    (access_specifier
      "protected") @visibility.protected
    """,

    # Operator overloading
    "operators": """
    (function_definition
      declarator: (function_declarator
        declarator: (operator_name) @operator_name
        parameters: (parameter_list) @operator_params)
      body: (compound_statement) @operator_body)
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
    """,

    # Variable declarations
    "variable_declarations": """
    (declaration) @variable_declaration
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
