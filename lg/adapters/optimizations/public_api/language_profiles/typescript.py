"""
Element profiles for TypeScript language.

TypeScript has explicit visibility modifiers (public, private, protected)
and export keyword for top-level declarations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_namespace(node: Node) -> bool:
    """Check if node is inside namespace (internal_module)."""
    current = node.parent
    while current:
        if current.type == "internal_module":
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False


def is_inside_class(node: Node) -> bool:
    """Check if node is inside class definition."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body"):
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False


def is_side_effect_import(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if import is side-effect only (must be preserved).

    Side-effect imports: import './module' (no destructuring, no 'from')
    These can modify global state and must not be removed.
    """
    import_text = doc.get_node_text(node)
    # Side-effect if no 'from', no '{', no '* as'
    return ("from" not in import_text) and ("{" not in import_text) and ("* as" not in import_text)


# Removed get_member_visibility_in_exported_class - use standard visibility logic
# Protected members should be filtered out in public API mode


def has_export_keyword(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node has 'export' keyword directly before it.

    For namespace members, checks if function itself has export.
    """
    node_text = doc.get_node_text(node).strip()

    # Check direct export keyword in text
    if node_text.startswith("export "):
        return True

    # Check parent for export_statement
    # If parent is export_statement, this means "export function ..." in source
    if node.parent and node.parent.type == "export_statement":
        return True

    return False


# TypeScript element profiles

TYPESCRIPT_PROFILES = LanguageElementProfiles(
    language="typescript",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Interfaces ===

        ElementProfile(
            name="interface",
            query="(interface_declaration) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Type Aliases ===

        ElementProfile(
            name="type",
            query="(type_alias_declaration) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Enums ===

        ElementProfile(
            name="enum",
            query="(enum_declaration) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Namespaces ===

        ElementProfile(
            name="namespace",
            query="(internal_module) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Functions ===
        # Top-level function declarations and namespace members

        # Top-level functions (not in class or namespace)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node) and not is_inside_namespace(node),
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # Functions inside namespace (must have explicit export to be public)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: is_inside_namespace(node),
            export_check=has_export_keyword,  # Custom check: only direct export counts
            uses_visibility_for_public_api=False  # Namespace members: use export
        ),

        # === Methods ===
        # Methods inside classes

        ElementProfile(
            name="method",
            query="(method_definition) @element",
            uses_visibility_for_public_api=True  # Members: use visibility (standard logic)
        ),

        # === Class Fields ===
        # Properties inside classes

        ElementProfile(
            name="field",
            query="(public_field_definition) @element",
            uses_visibility_for_public_api=True  # Members: use visibility (standard logic)
        ),

        # === Variables ===
        # Top-level const/let/var declarations

        ElementProfile(
            name="variable",
            query="(variable_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Imports ===
        # Preserve side-effect imports, remove others

        ElementProfile(
            name="import",
            query="(import_statement) @element",
            additional_check=lambda node, doc: not is_side_effect_import(node, doc),
            uses_visibility_for_public_api=False  # Imports: always remove (unless side-effect)
        ),
    ]
)
