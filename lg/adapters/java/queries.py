"""
Tree-sitter query definitions for Java language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (method_declaration
      name: (identifier) @function_name
      parameters: (formal_parameters) @function_params
      body: (block)? @function_body) @function_definition

    (constructor_declaration
      name: (identifier) @constructor_name
      parameters: (formal_parameters) @constructor_params
      body: (constructor_body) @constructor_body) @constructor_definition

    (lambda_expression
      parameters: (_) @lambda_params
      body: (_) @lambda_body) @function_definition
    """,

    # Comments (both single-line and block comments)
    "comments": """
    (line_comment) @comment

    (block_comment) @comment
    """,

    # Import statements
    "imports": """
    (import_declaration) @import
    """,

    # Class definitions
    "classes": """
    (class_declaration
      name: (identifier) @class_name
      body: (class_body) @class_body)
    """,

    # Interface definitions
    "interfaces": """
    (interface_declaration
      name: (identifier) @interface_name
      body: (interface_body) @interface_body)
    """,

    # Enum declarations
    "enums": """
    (enum_declaration
      name: (identifier) @enum_name
      body: (enum_body) @enum_body)
    """,

    # Annotation type declarations
    "annotation_types": """
    (annotation_type_declaration
      name: (identifier) @annotation_name
      body: (annotation_type_body) @annotation_body)
    """,

    # Annotations
    "annotations": """
    (annotation
      name: (identifier) @annotation_name)

    (marker_annotation
      name: (identifier) @annotation_name)

    (annotation
      name: (scoped_identifier) @annotation_name)
    """,

    # Field declarations
    "fields": """
    (field_declaration
      declarator: (variable_declarator
        name: (identifier) @field_name))
    """,

    # Local variable declarations (top-level fields)
    "local_variables": """
    (local_variable_declaration
      declarator: (variable_declarator
        name: (identifier) @variable_name))
    """,

    # Literals for trimming
    "literals": """
    (string_literal) @string

    (decimal_integer_literal) @number

    (hex_integer_literal) @number

    (octal_integer_literal) @number

    (binary_integer_literal) @number

    (decimal_floating_point_literal) @number

    (hex_floating_point_literal) @number

    (array_initializer) @array

    ; Java collection factory methods (Java 9+)
    (method_invocation
      object: (identifier) @class_name
      (#any-of? @class_name "List" "Set" "Map")
      name: (identifier) @method_name
      (#any-of? @method_name "of" "ofEntries" "copyOf")
      arguments: (argument_list) @args) @array

    ; Arrays.asList() pattern
    (method_invocation
      object: (identifier) @arrays_class
      (#eq? @arrays_class "Arrays")
      name: (identifier) @method
      (#eq? @method "asList")
      arguments: (argument_list) @args) @array

    ; Stream.of() pattern
    (method_invocation
      object: (identifier) @stream_class
      (#eq? @stream_class "Stream")
      name: (identifier) @method
      (#eq? @method "of")
      arguments: (argument_list) @args) @array

    ; Double-brace initialization pattern
    ; new HashMap<>() {{ put(...); put(...); }}
    (object_creation_expression
      (class_body
        (block))) @object
    """,

    # Constructors
    "constructors": """
    (constructor_declaration
      name: (identifier) @constructor_name
      parameters: (formal_parameters) @constructor_params
      body: (constructor_body) @constructor_body) @constructor
    """,

    # Getters and Setters (by naming convention)
    "getters_setters": """
    (method_declaration
      name: (identifier) @method_name
      (#match? @method_name "^(get|set|is)[A-Z]")
      body: (block) @method_body) @getter_setter
    """,

    # Visibility modifiers
    "visibility": """
    (modifiers
      (public)) @visibility.public

    (modifiers
      (private)) @visibility.private

    (modifiers
      (protected)) @visibility.protected

    (modifiers
      (package)) @visibility.package
    """,
}
