"""
Element profiles for Python language.

Python uses naming conventions for visibility:
- __name__ (dunder methods) = public
- __name (double underscore) = private
- _name (single underscore) = protected
- name = public
"""
from __future__ import annotations

from ....tree_sitter_support import Node, TreeSitterDocument
from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_class(node: Node) -> bool:
    """Check if node is inside class definition."""
    current = node.parent
    while current:
        if current.type == "class_definition":
            return True
        if current.type in ("module", "program"):
            return False
        current = current.parent
    return False


# Python element profiles

PYTHON_PROFILES = LanguageElementProfiles(
    language="python",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_definition) @element"
        ),

        # === Functions and Methods ===
        # Python has single node type (function_definition) for both.
        # Distinguish via is_inside_class check.

        # Top-level functions
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            additional_check=lambda node, doc: not is_inside_class(node)
        ),

        # Methods inside classes
        ElementProfile(
            name="method",
            query="(function_definition) @element",
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        # === Module-level Variables ===
        # Only top-level assignments (not inside functions/classes)

        ElementProfile(
            name="variable",
            query="(assignment) @element",
            additional_check=lambda node, doc: not is_inside_class(node)
        ),
    ]
)
