"""
Element profiles for C language.

C uses static keyword for internal linkage (private elements).
No access specifiers like C++ (no classes).
Naming convention: Internal* or _* prefix indicates internal types.
"""
from __future__ import annotations

from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def has_static_specifier(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if node has static storage class specifier."""
    for child in node.children:
        if child.type == "storage_class_specifier":
            if "static" in doc.get_node_text(child):
                return True
    return False


def is_internal_by_naming(name: str) -> bool:
    """Check if name indicates internal type (Internal* or _* prefix)."""
    if not name:
        return False
    return name.startswith("Internal") or name.startswith("_")


def is_exported_c(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Custom export check for C.

    Exported unless:
    - Has static specifier
    - Has Internal* or _* naming (for types)

    Returns:
        True if exported (should keep)
    """
    # Not exported if static
    if has_static_specifier(node, doc):
        return False

    # Check naming convention for types
    if node.type in ("type_definition", "struct_specifier", "enum_specifier", "union_specifier"):
        # Extract name from node
        for child in node.children:
            if child.type in ("type_identifier", "identifier"):
                name = doc.get_node_text(child)
                if is_internal_by_naming(name):
                    return False

    return True  # Otherwise exported


# C element profiles

C_PROFILES = LanguageElementProfiles(
    language="c",
    profiles=[
        # === Functions ===
        # C doesn't have classes, all functions are top-level

        ElementProfile(
            name="function",
            query="(function_definition) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export (static keyword)
        ),

        # === Structs ===

        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export (static or naming)
        ),

        # === Unions ===

        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export
        ),

        # === Enums ===

        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export (naming)
        ),

        # === Typedefs ===

        ElementProfile(
            name="typedef",
            query="(type_definition) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export (naming)
        ),

        # === Variables ===
        # Global variable declarations

        ElementProfile(
            name="variable",
            query="(declaration) @element",
            export_check=is_exported_c,
            uses_visibility_for_public_api=False  # C: use export (static)
        ),
    ]
)
