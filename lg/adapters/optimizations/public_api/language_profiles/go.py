"""
Element profiles for Go language.

Go uses naming convention for visibility:
- Uppercase first letter = exported (public)
- Lowercase first letter = unexported (private)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def go_visibility_check(node: Node, doc: TreeSitterDocument) -> str:
    """
    Go visibility determined by case of first letter.
    Uppercase = public, lowercase = private.
    """
    # Get element name
    name_node = node.child_by_field_name("name")
    if not name_node:
        # Try to get name from node itself
        name_text = doc.get_node_text(node)
        if name_text:
            return "public" if name_text[0].isupper() else "private"
        return "public"

    name = doc.get_node_text(name_node)
    if not name:
        return "public"

    # Go convention: uppercase = exported
    return "public" if name[0].isupper() else "private"


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


def is_type_alias_not_struct_or_interface(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if type_declaration is a type alias (not struct or interface).

    Type aliases don't have struct_type or interface_type children.
    """
    # node is type_identifier from query, parent is type_spec
    type_spec = node.parent
    if not type_spec or type_spec.type != "type_spec":
        return False

    # Check if type_spec has struct_type or interface_type
    for child in type_spec.children:
        if child.type in ("struct_type", "interface_type"):
            return False  # This is struct or interface, not type alias

    return True  # This is type alias


# Go element profiles

GO_PROFILES = LanguageElementProfiles(
    language="go",
    profiles=[
        # === Structs ===

        ElementProfile(
            name="struct",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier) @element
                type: (struct_type)
              )
            )
            """,
            visibility_check=go_visibility_check
        ),

        # === Interfaces ===

        ElementProfile(
            name="interface",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier) @element
                type: (interface_type)
              )
            )
            """,
            visibility_check=go_visibility_check
        ),

        # === Type Aliases ===
        # Exclude structs and interfaces (they have their own profiles)

        ElementProfile(
            name="type",
            query="""
            (type_declaration
              (type_spec
                name: (type_identifier) @element
              )
            )
            """,
            visibility_check=go_visibility_check,
            additional_check=is_type_alias_not_struct_or_interface
        ),

        # === Functions ===

        ElementProfile(
            name="function",
            query="(function_declaration name: (identifier) @element)",
            visibility_check=go_visibility_check
        ),

        # === Methods ===

        ElementProfile(
            name="method",
            query="(method_declaration name: (field_identifier) @element)",
            # Methods never exported directly
            export_check=lambda node, doc: False
        ),

        # === Variables and Constants ===
        # Only module-level (not inside functions)

        ElementProfile(
            name="variable",
            query="""
            (var_declaration
              (var_spec name: (identifier) @element)
            )
            """,
            visibility_check=go_visibility_check,
            additional_check=lambda node, doc: not is_inside_function(node)
        ),

        ElementProfile(
            name="constant",
            query="""
            (const_declaration
              (const_spec name: (identifier) @element)
            )
            """,
            visibility_check=go_visibility_check,
            additional_check=lambda node, doc: not is_inside_function(node)
        ),

        # === Struct Fields ===
        # Only private fields in exported structs

        ElementProfile(
            name="field",
            query="""
            (field_declaration
              name: (field_identifier) @element
            )
            """,
            visibility_check=go_visibility_check,
            additional_check=lambda node, doc: is_in_exported_struct(node, doc)
        ),
    ]
)
