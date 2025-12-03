"""
Tree-sitter query definitions for Rust language.
Contains S-expression queries for structural code analysis.
"""

from __future__ import annotations

QUERIES = {
    # Functions and methods
    "functions": """
    (function_item
      name: (identifier) @function_name
      parameters: (parameters) @function_params
      body: (block)? @function_body) @function_definition

    (function_signature_item
      name: (identifier) @function_name
      parameters: (parameters) @function_params) @function_definition

    (closure_expression
      parameters: (closure_parameters) @lambda_params
      body: (_) @lambda_body) @function_definition
    """,

    # Comments (including doc comments)
    "comments": """
    (line_comment) @comment

    (block_comment) @comment

    (line_comment
      (doc_comment)) @comment.doc

    (block_comment
      (doc_comment)) @comment.doc
    """,

    # Use declarations (imports)
    "imports": """
    (use_declaration) @import

    (extern_crate_declaration) @import
    """,

    # Struct definitions (class equivalent)
    "classes": """
    (struct_item
      name: (type_identifier) @struct_name
      body: (field_declaration_list) @struct_body)

    (struct_item
      name: (type_identifier) @struct_name)

    (enum_item
      name: (type_identifier) @enum_name
      body: (enum_variant_list) @enum_body)

    (union_item
      name: (type_identifier) @union_name
      body: (field_declaration_list) @union_body)
    """,

    # Struct fields
    "struct_fields": """
    (field_declaration
      (visibility_modifier)? @field_visibility
      name: (field_identifier) @field_name
      type: (_) @field_type)
    """,

    # Trait definitions
    "traits": """
    (trait_item
      name: (type_identifier) @trait_name
      body: (declaration_list) @trait_body)
    """,

    # Implementation blocks
    "impls": """
    (impl_item
      type: (type_identifier) @impl_type
      body: (declaration_list) @impl_body) @impl_block

    (impl_item
      trait: (type_identifier) @impl_trait
      type: (type_identifier) @impl_type
      body: (declaration_list) @impl_body) @trait_impl
    """,

    # Type aliases
    "type_aliases": """
    (type_item
      name: (type_identifier) @type_alias_name
      type: (_) @type_alias_value)
    """,

    # Enum variants
    "enums": """
    (enum_item
      name: (type_identifier) @enum_name
      body: (enum_variant_list) @enum_body)

    (enum_variant
      name: (identifier) @variant_name)

    (enum_variant
      name: (identifier) @variant_name
      body: (field_declaration_list) @variant_body)
    """,

    # Module definitions
    "modules": """
    (mod_item
      name: (identifier) @module_name
      body: (declaration_list) @module_body)

    (mod_item
      name: (identifier) @module_name) @module_declaration
    """,

    # Macro definitions and invocations
    "macros": """
    (macro_definition
      name: (identifier) @macro_name
      (macro_rule)+ @macro_rules) @macro_def

    (macro_invocation
      macro: (identifier) @macro_name
      (token_tree) @macro_args) @macro_call

    (macro_invocation
      macro: (scoped_identifier
        name: (identifier) @macro_name)
      (token_tree) @macro_args) @macro_call
    """,

    # Attributes (Rust's annotations)
    "attributes": """
    (attribute_item
      (attribute) @attribute)

    (attribute_item
      (attribute
        (identifier) @attribute_name))

    (inner_attribute_item
      (attribute) @inner_attribute)
    """,

    # Visibility modifiers
    "visibility": """
    (visibility_modifier
      "pub") @visibility.public

    (visibility_modifier
      "pub"
      (crate)) @visibility.pub_crate

    (visibility_modifier
      "pub"
      (super)) @visibility.pub_super

    (visibility_modifier
      "pub"
      (self)) @visibility.pub_self

    (visibility_modifier
      "pub"
      (in)
      (identifier) @visibility_scope) @visibility.pub_in
    """,

    # Literals for trimming
    "literals": """
    (string_literal) @string

    (raw_string_literal) @string

    (char_literal) @string

    (integer_literal) @number

    (float_literal) @number

    (boolean_literal) @boolean

    (array_expression) @array

    (tuple_expression) @array

    ; Rust vec! macro
    (macro_invocation
      macro: (identifier) @macro_name
      (#eq? @macro_name "vec")
      (token_tree)) @array

    ; Rust lazy_static! macro with HashMap
    (macro_invocation
      macro: (identifier) @macro_name
      (#eq? @macro_name "lazy_static")
      (token_tree)) @object

    ; HashMap initialization blocks (block as let_declaration value)
    (let_declaration
      value: (block) @array)
    """,

    # Variable declarations
    "variables": """
    (let_declaration
      pattern: (identifier) @var_name
      type: (_)? @var_type
      value: (_)? @var_value)

    (const_item
      name: (identifier) @const_name
      type: (_) @const_type
      value: (_) @const_value)

    (static_item
      name: (identifier) @static_name
      type: (_) @static_type
      value: (_)? @static_value)
    """,

    # Pattern matching
    "pattern_matching": """
    (match_expression
      value: (_) @match_value
      body: (match_block) @match_body)

    (match_arm
      pattern: (_) @match_pattern
      value: (_) @match_value)
    """,

    # Associated functions and methods (in impl blocks)
    "impl_functions": """
    (impl_item
      body: (declaration_list
        (function_item
          name: (identifier) @impl_function_name
          parameters: (parameters) @impl_function_params
          body: (block) @impl_function_body)))
    """,
}
