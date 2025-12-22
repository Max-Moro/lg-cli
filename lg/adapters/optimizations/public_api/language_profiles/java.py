"""
Element profiles for Java language.

Java has simpler structure than Scala - no traits, objects, or case classes.
Standard visibility modifiers: public, private, protected, package-private (default).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_class(node: Node) -> bool:
    """Check if node is inside class or interface."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "interface_declaration", "class_body", "interface_body"):
            return True
        if current.type == "program":
            break
        current = current.parent
    return False


def is_inside_method_or_constructor(node: Node) -> bool:
    """Check if node is inside method or constructor body."""
    current = node.parent
    while current:
        if current.type in ("method_declaration", "constructor_declaration", "block"):
            # Check if block is method/constructor body
            if current.type == "block" and current.parent:
                if current.parent.type in ("method_declaration", "constructor_declaration"):
                    return True
            elif current.type in ("method_declaration", "constructor_declaration"):
                return True
        if current.type in ("class_body", "program"):
            break
        current = current.parent
    return False


# Java element profiles

JAVA_PROFILES = LanguageElementProfiles(
    language="java",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_declaration name: (identifier) @element)"
        ),

        # === Interfaces ===

        ElementProfile(
            name="interface",
            query="(interface_declaration name: (identifier) @element)"
        ),

        # === Enums ===

        ElementProfile(
            name="enum",
            query="(enum_declaration name: (identifier) @element)"
        ),

        # === Annotation Types ===

        ElementProfile(
            name="annotation",
            query="(annotation_type_declaration name: (identifier) @element)"
        ),

        # === Functions and Methods ===

        ElementProfile(
            name="method",
            query="(method_declaration name: (identifier) @element)"
        ),

        ElementProfile(
            name="constructor",
            query="(constructor_declaration name: (identifier) @element)"
        ),

        # === Class Fields ===
        # Only fields inside classes (not top-level, which are invalid Java but may appear in tests)

        ElementProfile(
            name="field",
            query="(field_declaration declarator: (variable_declarator name: (identifier) @element))",
            additional_check=lambda node, doc: is_inside_class(node)
        ),

        # === Local Variables ===
        # Variables inside methods AND top-level (Java tree-sitter parses top-level as local_variable_declaration)
        # Visibility check will handle public vs private for top-level

        ElementProfile(
            name="variable",
            query="(local_variable_declaration declarator: (variable_declarator name: (identifier) @element))"
        ),
    ]
)
