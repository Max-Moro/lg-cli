"""
Go code profiles for declarative element collection.

Describes all code element types in Go:
- Type declarations (struct, interface, type alias)
- Structs (as types)
- Interfaces (as types)
- Functions (top-level)
- Methods (receiver functions)
- Constants
- Variables

Go uses naming conventions for visibility:
- Names starting with uppercase letter = exported (public)
- Names starting with lowercase letter = unexported (private)
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor
from ...tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_inside_function_or_method(node: Node) -> bool:
    """Check if node is inside function or method body."""
    current = node.parent
    while current:
        if current.type in ("function_declaration", "method_declaration", "func_literal", "block"):
            # For block, verify it's a function/method body
            if current.type == "block" and current.parent:
                if current.parent.type in ("function_declaration", "method_declaration", "func_literal"):
                    return True
            elif current.type in ("function_declaration", "method_declaration", "func_literal"):
                return True
        if current.type in ("source_file", "package_clause"):
            break
        current = current.parent
    return False


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Go element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # For type declarations, look inside type_spec or type_alias
    if node.type == "type_declaration":
        for child in node.children:
            if child.type in ("type_spec", "type_alias"):
                for grandchild in child.children:
                    if grandchild.type == "type_identifier":
                        return doc.get_node_text(grandchild)

    # For method declarations, get field_identifier (method name)
    if node.type == "method_declaration":
        for child in node.children:
            if child.type == "field_identifier":
                return doc.get_node_text(child)

    # For var/const declarations
    if node.type in ("var_declaration", "const_declaration"):
        for child in node.children:
            if child.type in ("var_spec", "const_spec"):
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    # For short variable declarations
    if node.type == "short_var_declaration":
        for child in node.children:
            if child.type == "expression_list":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    # For field declarations (struct fields)
    if node.type == "field_declaration":
        for child in node.children:
            if child.type == "field_identifier":
                return doc.get_node_text(child)

    # Generic search for identifier/field_identifier child
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _is_public_go(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Go element is public based on naming convention.

    Rules:
    - Names starting with uppercase letter = exported (public)
    - Names starting with lowercase letter = unexported (private)

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    name = _extract_name(node, doc)
    if not name:
        return True  # No name = public by default

    # Go convention: uppercase first letter = exported (public)
    return name[0].isupper()


def _determine_type_kind(node: Node) -> Optional[str]:
    """
    Determine the kind of type declaration (struct, interface, or alias).

    Args:
        node: type_declaration node

    Returns:
        String: "struct", "interface", or "alias", or None if not determined
    """
    for child in node.children:
        if child.type == "type_spec":
            for grandchild in child.children:
                if grandchild.type == "struct_type":
                    return "struct"
                elif grandchild.type == "interface_type":
                    return "interface"
            # If type_spec but no struct_type or interface_type, it's an alias
            return "alias"
        elif child.type == "type_alias":
            return "alias"
    return None


# --- Go Code Descriptor ---

GO_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="go",
    profiles=[
        # === Type Declarations (Structs) ===
        # Struct types defined via type declaration
        ElementProfile(
            name="struct",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier)
                type: (struct_type))) @element
            """,
            is_public=_is_public_go,
        ),

        # === Type Declarations (Interfaces) ===
        # Interface types defined via type declaration
        ElementProfile(
            name="interface",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier)
                type: (interface_type))) @element
            """,
            is_public=_is_public_go,
        ),

        # === Type Declarations (Aliases) ===
        # Type aliases and other type declarations
        ElementProfile(
            name="type",
            query="(type_declaration) @element",
            is_public=_is_public_go,
            additional_check=lambda node, doc: _determine_type_kind(node) == "alias",
        ),

        # === Functions (Top-level) ===
        ElementProfile(
            name="function",
            query="""
            (function_declaration
              name: (identifier)
              body: (block)) @element
            """,
            is_public=_is_public_go,
            has_body=True,
        ),

        # === Methods (Functions with Receiver) ===
        ElementProfile(
            name="method",
            query="""
            (method_declaration
              receiver: (parameter_list)
              name: (field_identifier)
              body: (block)) @element
            """,
            is_public=_is_public_go,
            has_body=True,
        ),

        # === Constants (Package-level) ===
        ElementProfile(
            name="constant",
            query="""
            (const_declaration
              (const_spec
                name: (identifier))) @element
            """,
            is_public=_is_public_go,
            additional_check=lambda node, doc: not _is_inside_function_or_method(node),
        ),

        # === Variables (Package-level) ===
        ElementProfile(
            name="variable",
            query="""
            (var_declaration
              (var_spec
                name: (identifier))) @element
            """,
            is_public=_is_public_go,
            additional_check=lambda node, doc: not _is_inside_function_or_method(node),
        ),

        # === Struct Fields ===
        # Fields inside struct types
        ElementProfile(
            name="field",
            query="""
            (field_declaration
              name: (field_identifier)) @element
            """,
            is_public=_is_public_go,
        ),
    ],

    decorator_types=set(),  # Go doesn't have decorators
    comment_types={"comment", "line_comment", "block_comment"},
    name_extractor=_extract_name,
)


__all__ = ["GO_CODE_DESCRIPTOR"]
