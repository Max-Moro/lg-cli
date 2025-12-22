"""
Element profiles for Go language.

Go uses naming convention for visibility:
- Uppercase first letter = exported (public)
- Lowercase first letter = unexported (private)
"""
from __future__ import annotations

from typing import Optional

from ....tree_sitter_support import Node, TreeSitterDocument
from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_function(node: Node) -> bool:
    """Check if node is inside function body."""
    current = node.parent
    while current:
        if current.type == "block":
            if current.parent and current.parent.type in ("function_declaration", "method_declaration"):
                return True
        if current.type == "source_file":
            return False
        current = current.parent
    return False


def is_in_exported_struct(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if field is in exported struct."""
    current = node.parent
    while current:
        if current.type == "type_spec":
            for child in current.children:
                if child.type == "type_identifier":
                    name = doc.get_node_text(child)
                    return name[0].isupper() if name else False
        if current.type == "source_file":
            break
        current = current.parent
    return False


def _get_declaration_visibility(node: Node, doc: TreeSitterDocument, identifier_type: str) -> str:
    """
    Get visibility of declaration node by finding the name identifier.

    Args:
        node: Declaration node (function_declaration, var_declaration, etc.)
        doc: TreeSitterDocument
        identifier_type: Type of identifier to look for ("identifier", "field_identifier")

    Returns:
        "public" if exported (uppercase), "private" otherwise
    """
    # Find identifier of specified type
    def find_identifier(n: Node) -> Optional[Node]:
        if n.type == identifier_type:
            return n
        for child in n.children:
            result = find_identifier(child)
            if result:
                return result
        return None

    identifier = find_identifier(node)
    if not identifier:
        return "public"

    name = doc.get_node_text(identifier)
    if not name:
        return "public"

    # Go convention: uppercase = public
    return "public" if name[0].isupper() else "private"


def _get_type_visibility(node: Node, doc: TreeSitterDocument) -> str:
    """
    Get visibility of type_declaration by finding the type name identifier.

    Args:
        node: type_declaration node
        doc: TreeSitterDocument

    Returns:
        "public" if exported (uppercase), "private" otherwise
    """
    # Find type_identifier in type_spec or type_alias
    def find_type_identifier(n: Node) -> Optional[Node]:
        if n.type == "type_identifier":
            # Check if this is the name (first identifier in type_spec/type_alias)
            parent = n.parent
            if parent and parent.type in ("type_spec", "type_alias"):
                # Get first type_identifier child (that's the name)
                for child in parent.children:
                    if child.type == "type_identifier":
                        return child
        for child in n.children:
            result = find_type_identifier(child)
            if result:
                return result
        return None

    identifier = find_type_identifier(node)
    if not identifier:
        return "public"

    name = doc.get_node_text(identifier)
    if not name:
        return "public"

    # Go convention: uppercase = public
    return "public" if name[0].isupper() else "private"


def _has_struct_or_interface(node: Node) -> bool:
    """
    Check if type_declaration contains struct_type or interface_type.

    Args:
        node: type_declaration node

    Returns:
        True if this is struct or interface definition
    """
    def has_type_recursive(n: Node) -> bool:
        if n.type in ("struct_type", "interface_type"):
            return True
        for child in n.children:
            if has_type_recursive(child):
                return True
        return False

    return has_type_recursive(node)


# Go element profiles

GO_PROFILES = LanguageElementProfiles(
    language="go",
    profiles=[
        # === Structs ===

        ElementProfile(
            name="struct",
            query="(type_declaration (type_spec type: (struct_type))) @element",
            visibility_check=lambda node, doc: _get_type_visibility(node, doc)
        ),

        # === Interfaces ===

        ElementProfile(
            name="interface",
            query="(type_declaration (type_spec type: (interface_type))) @element",
            visibility_check=lambda node, doc: _get_type_visibility(node, doc)
        ),

        # === Type Aliases ===
        # Go type aliases use type_alias node (with =)
        # Example: type UserID = int

        ElementProfile(
            name="type",
            query="(type_declaration (type_alias)) @element",
            visibility_check=lambda node, doc: _get_type_visibility(node, doc)
        ),

        # === Type Definitions ===
        # Go type definitions use type_spec node (without =)
        # Example: type UserRole string
        # Exclude structs and interfaces (they have their own profiles)

        ElementProfile(
            name="type",
            query="(type_declaration (type_spec)) @element",
            visibility_check=lambda node, doc: _get_type_visibility(node, doc),
            additional_check=lambda node, doc: not _has_struct_or_interface(node)
        ),

        # === Functions ===

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            visibility_check=lambda node, doc: _get_declaration_visibility(node, doc, "identifier")
        ),

        # === Methods ===

        ElementProfile(
            name="method",
            query="(method_declaration) @element",
            visibility_check=lambda node, doc: _get_declaration_visibility(node, doc, "field_identifier"),
            # Methods never exported directly
            export_check=lambda node, doc: False
        ),

        # === Variables and Constants ===
        # Only module-level (not inside functions)

        ElementProfile(
            name="variable",
            query="(var_declaration) @element",
            visibility_check=lambda node, doc: _get_declaration_visibility(node, doc, "identifier"),
            additional_check=lambda node, doc: not is_inside_function(node)
        ),

        ElementProfile(
            name="constant",
            query="(const_declaration) @element",
            visibility_check=lambda node, doc: _get_declaration_visibility(node, doc, "identifier"),
            additional_check=lambda node, doc: not is_inside_function(node)
        ),

        # === Struct Fields ===
        # Only private fields in exported structs

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            visibility_check=lambda node, doc: _get_declaration_visibility(node, doc, "field_identifier"),
            additional_check=lambda node, doc: is_in_exported_struct(node, doc)
        ),
    ]
)
