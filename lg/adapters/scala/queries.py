"""
Tree-sitter query definitions for Scala language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_definition
      name: (identifier) @function_name
      parameters: (parameters) @function_params
      body: (_) @function_body) @function_definition

    (function_declaration
      name: (identifier) @function_name
      parameters: (parameters) @function_params) @function_declaration

    (lambda_expression
      parameters: (bindings) @lambda_params
      body: (_) @lambda_body) @function_definition
    """,

    # Comments
    "comments": """
    (comment) @comment

    (block_comment) @comment
    """,

    # Import statements
    "imports": """
    (import_declaration) @import

    (import_declaration
      path: (_) @import_path)
    """,

    # Class definitions
    "classes": """
    (class_definition
      name: (identifier) @class_name
      body: (template_body) @class_body)
    """,

    # Object definitions (singletons)
    "objects": """
    (object_definition
      name: (identifier) @object_name
      body: (template_body) @object_body)
    """,

    # Trait definitions
    "traits": """
    (trait_definition
      name: (identifier) @trait_name
      body: (template_body) @trait_body)

    (trait_definition
      name: (identifier) @trait_name)
    """,

    # Case class definitions
    "case_classes": """
    (class_definition
      name: (identifier) @case_class_name
      parameters: (class_parameters)? @case_class_params) @class_definition
    """,

    # Class members (fields and methods)
    "class_members": """
    (template_body
      (function_definition
        name: (identifier) @method_name)) @method_definition

    (template_body
      (val_definition
        pattern: (identifier) @field_name)) @field_definition

    (template_body
      (var_definition
        pattern: (identifier) @field_name)) @field_definition
    """,

    # Enum definitions
    "enums": """
    (enum_definition
      name: (identifier) @enum_name
      body: (enum_body) @enum_body)

    (simple_enum_case
      name: (identifier) @enum_case_name)

    (full_enum_case
      name: (identifier) @enum_case_name
      parameters: (class_parameters) @enum_case_params)
    """,

    # Type definitions and aliases
    "type_aliases": """
    (type_definition
      name: (type_identifier) @type_name
      type: (_) @type_value)
    """,

    # Variable declarations
    "variables": """
    (val_definition
      pattern: (identifier) @val_name
      value: (_) @val_value)

    (var_definition
      pattern: (identifier) @var_name
      value: (_) @var_value)

    (val_declaration
      name: (identifier) @val_name)

    (var_declaration
      name: (identifier) @var_name)

    (given_definition
      name: (identifier) @given_name)
    """,

    # Constructors
    "constructors": """
    (class_definition
      parameters: (class_parameters) @primary_constructor_params)

    (function_definition
      name: (identifier) @constructor_name
      (#match? @constructor_name "^this$")
      parameters: (parameters) @constructor_params
      body: (_) @constructor_body)
    """,

    # Visibility modifiers
    "visibility": """
    (modifiers
      (access_modifier
        "private")) @visibility.private

    (modifiers
      (access_modifier
        "protected")) @visibility.protected

    (modifiers
      (access_modifier
        "private"
        (access_qualifier))) @visibility.private.qualified

    (modifiers
      (access_modifier
        "protected"
        (access_qualifier))) @visibility.protected.qualified
    """,

    # Annotations
    "annotations": """
    (annotation
      name: (identifier) @annotation_name)

    (annotation
      name: (simple_type
        name: (type_identifier) @annotation_name))
    """,

    # Literals for trimming
    "literals": """
    (string) @string

    (interpolated_string) @string

    (interpolated_string_expression) @string

    (symbol_literal) @string

    (character_literal) @string

    (integer_literal) @number

    (floating_point_literal) @number

    (boolean_literal) @boolean
    """,

    # Pattern matching
    "pattern_matching": """
    (match_expression
      value: (_) @match_value
      body: (case_block) @match_body)

    (case_clause
      pattern: (_) @case_pattern
      body: (_) @case_body)
    """,

    # Package declarations
    "packages": """
    (package_clause
      name: (package_identifier) @package_name)

    (package_object
      name: (identifier) @package_object_name
      body: (template_body) @package_object_body)
    """,
}
