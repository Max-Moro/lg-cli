"""
Element profiles for JavaScript language.

JavaScript uses convention-based visibility (_ prefix) and ES2022+ private fields (#).
Export keyword for top-level declarations.
"""
from __future__ import annotations

from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_class(node: Node) -> bool:
    """Check if node is inside class definition."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body", "class"):
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False


# JavaScript element profiles

JAVASCRIPT_PROFILES = LanguageElementProfiles(
    language="javascript",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Functions ===
        # Top-level function declarations

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Methods ===
        # Methods inside classes (both public and private with #)

        ElementProfile(
            name="method",
            query="(method_definition) @element",
            uses_visibility_for_public_api=True  # Members: use visibility (standard logic handles # and _)
        ),

        # === Class Fields ===
        # Properties inside classes (both public and ES2022+ private with #)

        ElementProfile(
            name="field",
            query="(field_definition) @element",
            uses_visibility_for_public_api=True  # Members: use visibility (standard logic handles # and _)
        ),

        # === Variables ===
        # Top-level const/let/var declarations

        ElementProfile(
            name="variable",
            query="(variable_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # Lexical declarations (const, let)
        ElementProfile(
            name="variable",
            query="(lexical_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            uses_visibility_for_public_api=False  # Top-level: use export
        ),

        # === Imports ===
        # All imports are private unless re-exported

        ElementProfile(
            name="import",
            query="(import_statement) @element",
            uses_visibility_for_public_api=False  # Imports: always remove (unless re-exported)
        ),
    ]
)
