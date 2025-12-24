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


# --- Helper functions ---


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

    Args:
        name: Element name to check

    Returns:
        True if name follows internal convention
    """
    if not name:
        return False
    return name.startswith("Internal") or name.startswith("_")


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of C element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # For function definitions, look for function_declarator
    if node.type == "function_definition":
        for child in node.children:
            if child.type in ("function_declarator", "pointer_declarator"):
                name = _extract_function_name(child, doc)
                if name:
                    return name

    # For type definitions
    if node.type == "type_definition":
        for child in reversed(node.children):
            if child.type == "type_identifier":
                return doc.get_node_text(child)

    # Search for child node with name
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _extract_function_name(declarator: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract function name from function_declarator or pointer_declarator.

    Args:
        declarator: Declarator node
        doc: Tree-sitter document

    Returns:
        Function name or None
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

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    # Check for static storage class specifier (private)
    if _has_static_specifier(node, doc):
        return False

    # Check naming convention for types and variables
    if node.type in ("type_definition", "struct_specifier", "enum_specifier", "union_specifier"):
        name = _extract_name(node, doc)
        if _is_internal_by_naming(name):
            return False

    # For declarations (variables), check naming
    if node.type == "declaration":
        name = _extract_name(node, doc)
        if _is_internal_by_naming(name):
            return False

    return True  # Otherwise public


# --- C Code Descriptor ---

C_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="c",
    profiles=[
        # === Functions ===
        # C doesn't have classes, all functions are top-level
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_c,
            has_body=True,
        ),

        # === Structs ===
        # Struct definitions (not declarations in function signatures)
        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            is_public=_is_public_c,
        ),

        # === Unions ===
        # Union type definitions
        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            is_public=_is_public_c,
        ),

        # === Enums ===
        # Enum type definitions
        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            is_public=_is_public_c,
        ),

        # === Typedefs ===
        # Type definitions (typedef)
        ElementProfile(
            name="typedef",
            query="(type_definition) @element",
            is_public=_is_public_c,
        ),

        # === Variables ===
        # Global variable declarations (not inside functions)
        ElementProfile(
            name="variable",
            query="(declaration) @element",
            is_public=_is_public_c,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"function_definition"}
            ),
        ),
    ],

    decorator_types=set(),  # C doesn't have decorators
    comment_types={"comment"},  # C has single comment type in tree-sitter
    name_extractor=_extract_name,
)


__all__ = ["C_CODE_DESCRIPTOR"]
