"""
C code profiles for declarative element collection.

Describes all code element types in C:
- Functions (top-level)
- Structs
- Unions
- Enums
- Typedefs
- Variables (global)

C doesn't have OOP visibility modifiers (no classes, no private/protected/public).
Visibility is determined by:
- static keyword (file-local/private)
- Default (no static) = external linkage (public)
- Naming convention: Internal* or _* prefix indicates internal types
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _has_static_specifier(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if node has static storage class specifier."""
    for child in node.children:
        if child.type == "storage_class_specifier":
            if "static" in doc.get_node_text(child):
                return True
    return False


def _is_internal_by_naming(name: Optional[str]) -> bool:
    """
    Check if name indicates internal type (Internal* or _* prefix).
    """
    if not name:
        return False
    return name.startswith("Internal") or name.startswith("_")


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of C element from node.
    """
    if node.type == "function_definition":
        for child in node.children:
            if child.type in ("function_declarator", "pointer_declarator"):
                name = _extract_function_name(child, doc)
                if name:
                    return name

    if node.type == "type_definition":
        for child in reversed(node.children):
            if child.type == "type_identifier":
                return doc.get_node_text(child)

    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _extract_function_name(declarator: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract function name from function_declarator or pointer_declarator.
    """
    for child in declarator.children:
        if child.type == "identifier":
            return doc.get_node_text(child)
        elif child.type in ("function_declarator", "pointer_declarator"):
            # Recursive search in nested declarators
            name = _extract_function_name(child, doc)
            if name:
                return name
    return None


def _is_public_c(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if C element is public based on visibility rules.

    Rules:
    - Elements with static specifier are private (file-local)
    - Types/variables with Internal* or _* prefix are private (internal)
    - Default (no static, no internal prefix) = public
    """
    if _has_static_specifier(node, doc):
        return False

    if node.type in ("type_definition", "struct_specifier", "enum_specifier", "union_specifier"):
        name = _extract_name(node, doc)
        if _is_internal_by_naming(name):
            return False

    if node.type == "declaration":
        name = _extract_name(node, doc)
        if _is_internal_by_naming(name):
            return False

    return True


C_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="c",
    profiles=[
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_c,
            has_body=True,
        ),

        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            is_public=_is_public_c,
        ),

        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            is_public=_is_public_c,
        ),

        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            is_public=_is_public_c,
        ),

        ElementProfile(
            name="typedef",
            query="(type_definition) @element",
            is_public=_is_public_c,
        ),

        ElementProfile(
            name="variable",
            query="(declaration) @element",
            is_public=_is_public_c,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"function_definition"}
            ),
        ),
    ],

    decorator_types=set(),
    comment_types={"comment"},
    name_extractor=_extract_name,
)


__all__ = ["C_CODE_DESCRIPTOR"]
