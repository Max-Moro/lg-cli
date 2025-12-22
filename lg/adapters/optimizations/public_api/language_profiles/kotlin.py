"""
Element profiles for Kotlin language.

Kotlin has explicit visibility modifiers (public, private, protected, internal).
Public is the default modifier for top-level declarations.
"""
from __future__ import annotations

from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_inside_class(node: Node) -> bool:
    """Check if node is inside class definition."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body", "object_declaration"):
            return True
        if current.type in ("source_file",):
            return False
        current = current.parent
    return False


# Kotlin element profiles

KOTLIN_PROFILES = LanguageElementProfiles(
    language="kotlin",
    profiles=[
        # === Classes ===

        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            uses_visibility_for_public_api=True  # Top-level: use visibility modifiers
        ),

        # === Object Declarations ===
        # Kotlin-specific: singleton objects and companion objects

        ElementProfile(
            name="object",
            query="(object_declaration) @element",
            uses_visibility_for_public_api=True  # Objects: use visibility modifiers
        ),

        # === Functions ===
        # Top-level function declarations

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: not is_inside_class(node),
            uses_visibility_for_public_api=True  # Top-level: use visibility modifiers
        ),

        # === Methods ===
        # Functions inside classes

        ElementProfile(
            name="method",
            query="(function_declaration) @element",
            additional_check=lambda node, doc: is_inside_class(node),
            uses_visibility_for_public_api=True  # Members: use visibility modifiers
        ),

        # === Properties ===
        # Kotlin properties (val/var/const val) - both top-level and class members

        ElementProfile(
            name="property",
            query="(property_declaration) @element",
            uses_visibility_for_public_api=True  # Properties: use visibility modifiers
        ),

        # === Secondary Constructors ===

        ElementProfile(
            name="constructor",
            query="(secondary_constructor) @element",
            uses_visibility_for_public_api=True  # Constructors: use visibility modifiers
        ),

        # === Init Blocks ===

        ElementProfile(
            name="init",
            query="(anonymous_initializer) @element",
            uses_visibility_for_public_api=True  # Init blocks: use visibility modifiers
        ),

        # === Getters/Setters ===

        ElementProfile(
            name="getter",
            query="(getter) @element",
            uses_visibility_for_public_api=True  # Getters: use visibility modifiers
        ),

        ElementProfile(
            name="setter",
            query="(setter) @element",
            uses_visibility_for_public_api=True  # Setters: use visibility modifiers
        ),

        # === Misparsed Classes ===
        # Tree-sitter sometimes misparsed classes with multiple annotations as infix_expression
        # Requires both additional_check (to filter) and custom visibility_check (text-based)

        ElementProfile(
            name="class",
            query="(infix_expression) @element",
            additional_check=lambda node, doc: _is_misparsed_private_class(node, doc),
            visibility_check=lambda node, doc: _get_misparsed_class_visibility(node, doc),
            uses_visibility_for_public_api=True  # Use custom visibility check
        ),
    ]
)


def _is_misparsed_private_class(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if infix_expression is a misparsed private/protected class.

    Tree-sitter Kotlin sometimes misparsed classes with multiple annotations:
    @Logged
    @Validate
    private class Foo {...}

    Becomes: annotated_expression -> infix_expression instead of class_declaration

    Args:
        node: infix_expression node
        doc: Document

    Returns:
        True if this is misparsed private class
    """
    node_text = doc.get_node_text(node)
    # Check if text contains "private class" or "protected class"
    return ("private class" in node_text or "protected class" in node_text)


def _get_misparsed_class_visibility(node: Node, doc: TreeSitterDocument) -> str:
    """
    Get visibility for misparsed class by parsing text.

    Args:
        node: infix_expression node
        doc: Document

    Returns:
        "private", "protected", or "public"
    """
    node_text = doc.get_node_text(node)

    if "private" in node_text:
        return "private"
    elif "protected" in node_text:
        return "protected"
    else:
        return "public"
