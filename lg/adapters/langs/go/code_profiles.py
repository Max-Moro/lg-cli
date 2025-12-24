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

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Go element from node.
    """
    if node.type == "type_declaration":
        for child in node.children:
            if child.type in ("type_spec", "type_alias"):
                for grandchild in child.children:
                    if grandchild.type == "type_identifier":
                        return doc.get_node_text(grandchild)

    if node.type == "method_declaration":
        for child in node.children:
            if child.type == "field_identifier":
                return doc.get_node_text(child)

    if node.type in ("var_declaration", "const_declaration"):
        for child in node.children:
            if child.type in ("var_spec", "const_spec"):
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    if node.type == "short_var_declaration":
        for child in node.children:
            if child.type == "expression_list":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    if node.type == "field_declaration":
        for child in node.children:
            if child.type == "field_identifier":
                return doc.get_node_text(child)

    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

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
    """
    name = _extract_name(node, doc)
    if not name:
        return True  # No name = public by default

    # Go convention: uppercase first letter = exported (public)
    return name[0].isupper()


def _determine_type_kind(node: Node) -> Optional[str]:
    """
    Determine the kind of type declaration (struct, interface, or alias).
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


GO_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="go",
    profiles=[
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

        ElementProfile(
            name="type",
            query="(type_declaration) @element",
            is_public=_is_public_go,
            additional_check=lambda node, doc: _determine_type_kind(node) == "alias",
        ),

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

        ElementProfile(
            name="constant",
            query="""
            (const_declaration
              (const_spec
                name: (identifier))) @element
            """,
            is_public=_is_public_go,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"function_declaration", "method_declaration", "func_literal", "block"},
                boundary_types={"source_file", "package_clause"}
            ),
        ),

        ElementProfile(
            name="variable",
            query="""
            (var_declaration
              (var_spec
                name: (identifier))) @element
            """,
            is_public=_is_public_go,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"function_declaration", "method_declaration", "func_literal", "block"},
                boundary_types={"source_file", "package_clause"}
            ),
        ),

        ElementProfile(
            name="field",
            query="""
            (field_declaration
              name: (field_identifier)) @element
            """,
            is_public=_is_public_go,
        ),
    ],

    decorator_types=set(),
    comment_types={"comment", "line_comment", "block_comment"},
    name_extractor=_extract_name,
)


__all__ = ["GO_CODE_DESCRIPTOR"]
