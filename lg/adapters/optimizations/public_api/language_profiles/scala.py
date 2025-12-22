"""
Element profiles for Scala language.

Defines declarative profiles for all Scala element types that need to be
filtered in public API mode.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_case_class(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if class_definition is a case class."""
    node_text = doc.get_node_text(node)
    return "case class" in node_text[:50]


def is_inside_class(node: Node) -> bool:
    """Check if node is inside class/object/trait."""
    current = node.parent
    while current:
        if current.type in ("class_definition", "object_definition", "trait_definition", "template_body"):
            return True
        if current.type == "compilation_unit":
            break
        current = current.parent
    return False


# Scala element profiles

SCALA_PROFILES = LanguageElementProfiles(
    language="scala",
    profiles=[
        # === Classes ===
        # Regular classes (non-case)

        ElementProfile(
            name="class",
            query="(class_definition name: (identifier) @element)",
            additional_check=lambda node, doc: not is_case_class(node, doc)  # Exclude case classes
        ),

        # === Case Classes ===

        ElementProfile(
            name="case_class",
            query="(class_definition name: (identifier) @element)",
            additional_check=is_case_class  # Only case classes
        ),

        # === Traits ===

        ElementProfile(
            name="trait",
            query="(trait_definition name: (identifier) @element)"
        ),

        # === Objects ===

        ElementProfile(
            name="object",
            query="(object_definition name: (identifier) @element)"
        ),

        # === Type aliases ===

        ElementProfile(
            name="type",
            query="(type_definition name: (identifier) @element)"
        ),

        # === Functions and Methods ===
        # When using profiles, base CodeAnalyzer methods are NOT called.
        # Need to collect ALL functions and methods via profiles.

        ElementProfile(
            name="function",
            query="""
            (function_definition
              name: (identifier) @element
            )
            """,
            # Only top-level functions (not methods inside classes)
            additional_check=lambda node, doc: not is_inside_class(node)
        ),

        ElementProfile(
            name="method",
            query="""
            (function_definition
              name: (identifier) @element
            )
            """,
            # Only methods inside classes (not top-level functions)
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        # === Module-level variables/constants ===
        # val/var at module level (not inside classes)

        ElementProfile(
            name="variable",
            query="""
            (val_definition
              pattern: (identifier) @element
            )
            """,
            # Only module-level (not inside classes)
            additional_check=lambda node, doc: not is_inside_class(node)
        ),

        ElementProfile(
            name="variable",  # Same name for var
            query="""
            (var_definition
              pattern: (identifier) @element
            )
            """,
            additional_check=lambda node, doc: not is_inside_class(node)
        ),

        # === Class fields ===
        # val/var properties inside classes

        ElementProfile(
            name="field",
            query="""
            (val_definition
              pattern: (identifier) @element
            )
            """,
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        ElementProfile(
            name="field",  # Same name for var (both are "field")
            query="""
            (var_definition
              pattern: (identifier) @element
            )
            """,
            additional_check=lambda node, doc: is_inside_class(node)
        ),
    ]
)
