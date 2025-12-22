"""
Element profiles for C++ language.

C++ uses access specifiers (public:, private:, protected:) for visibility.
Export determined by: header files (all exported), static keyword, anonymous namespaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_class(node: Node) -> bool:
    """Check if node is inside class/struct definition."""
    current = node.parent
    while current:
        if current.type in ("class_specifier", "struct_specifier", "union_specifier", "field_declaration_list"):
            return True
        if current.type in ("namespace_definition", "translation_unit"):
            return False
        current = current.parent
    return False


def has_static_specifier(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if node has static storage class specifier."""
    for child in node.children:
        if child.type == "storage_class_specifier":
            if "static" in doc.get_node_text(child):
                return True
    return False


def in_anonymous_namespace(node: Node) -> bool:
    """Check if node is inside an anonymous namespace."""
    current = node.parent
    while current:
        if current.type == "namespace_definition":
            # Check if namespace has a name
            has_name = False
            for child in current.children:
                if child.type == "namespace_identifier":
                    has_name = True
                    break
            if not has_name:
                return True  # Anonymous namespace
        current = current.parent
    return False


def is_exported_cpp(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Custom export check for C++.

    Exported unless:
    - Has static specifier
    - In anonymous namespace

    Returns:
        True if exported (should be kept)
    """
    # Not exported if static
    if has_static_specifier(node, doc):
        return False

    # Not exported if in anonymous namespace
    if in_anonymous_namespace(node):
        return False

    return True  # Otherwise exported


# C++ element profiles

CPP_PROFILES = LanguageElementProfiles(
    language="cpp",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_specifier) @element",
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export (static/anonymous namespace)
        ),

        # === Structs ===

        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Unions ===

        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Enums ===

        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Namespaces ===

        ElementProfile(
            name="namespace",
            query="(namespace_definition) @element",
            # Only remove anonymous namespaces
            additional_check=lambda node, doc: not any(
                child.type == "namespace_identifier" for child in node.children
            ),
            uses_visibility_for_public_api=False
        ),

        # === Functions ===
        # Top-level function definitions

        ElementProfile(
            name="function",
            query="(function_definition) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export (static/anonymous namespace)
        ),

        # === Methods ===
        # Methods inside classes (collected via class_methods query)

        ElementProfile(
            name="method",
            query="(field_declaration_list (function_definition) @element)",
            uses_visibility_for_public_api=True  # Members: use visibility (access specifiers)
        ),

        # === Class Fields ===
        # Properties inside classes

        ElementProfile(
            name="field",
            query="(field_declaration_list (field_declaration) @element)",
            uses_visibility_for_public_api=True  # Members: use visibility (access specifiers)
        ),

        # === Variables ===
        # Top-level variable declarations

        ElementProfile(
            name="variable",
            query="(declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            export_check=is_exported_cpp,
            uses_visibility_for_public_api=False  # Top-level: use export (static)
        ),
    ]
)
