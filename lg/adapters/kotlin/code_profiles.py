"""
Kotlin code profiles for declarative element collection.

Describes all code element types in Kotlin:
- Classes
- Objects (Kotlin-specific: singletons and companion objects)
- Functions (top-level)
- Methods (inside classes)
- Properties (val/var/const val)
- Constructors (secondary constructors)
- Init blocks (anonymous initializers)
- Getters/Setters

Kotlin uses explicit visibility modifiers (public, private, protected, internal).
Public is the default modifier for top-level declarations.
"""

from __future__ import annotations

from typing import Optional

from ..optimizations.shared import ElementProfile, LanguageCodeDescriptor
from ..tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_inside_class(node: Node) -> bool:
    """Check if node is inside class or object definition."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body", "object_declaration"):
            return True
        if current.type in ("source_file",):
            return False
        current = current.parent
    return False


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Kotlin element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # Special handling for property_declaration
    if node.type == "property_declaration":
        for child in node.children:
            if child.type == "variable_declaration":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    # Search for child node with identifier
    for child in node.children:
        if child.type == "identifier":
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _get_visibility_modifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract visibility modifier from Kotlin node.

    Kotlin visibility modifiers: private, protected, internal, public

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Modifier text ("private", "protected", "internal", "public") or None
    """
    for child in node.children:
        if child.type == "modifiers":
            for modifier_child in child.children:
                if modifier_child.type == "visibility_modifier":
                    return doc.get_node_text(modifier_child).strip()
    return None


def _is_public_kotlin(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Kotlin element is public based on visibility modifiers.

    Kotlin rules:
    - private = private
    - protected = private (protected)
    - internal = internal (module-level, treated as private for public API)
    - public or no modifier = public (default)

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    modifier = _get_visibility_modifier(node, doc)

    # private, protected, internal = private
    if modifier in ("private", "protected", "internal"):
        return False

    # public or no modifier = public (default in Kotlin)
    return True


def _is_public_misparsed_class(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if misparsed class (infix_expression) is public.

    Tree-sitter sometimes misparsed classes with multiple annotations as infix_expression.
    This checks if it's explicitly marked as private or protected.

    Args:
        node: infix_expression node
        doc: Tree-sitter document

    Returns:
        True if element is public (not explicitly private)
    """
    node_text = doc.get_node_text(node)
    # If it has "private class" or "protected class" in the text, it's private
    if "private class" in node_text or "protected class" in node_text:
        return False
    return True


def _is_misparsed_class(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if infix_expression is a misparsed class (filter for class profile).

    Tree-sitter Kotlin sometimes misparsed classes with multiple annotations:
    @Logged
    @Validate
    private class Foo {...}

    Becomes: annotated_expression -> infix_expression instead of class_declaration

    Args:
        node: infix_expression node
        doc: Tree-sitter document

    Returns:
        True if this is misparsed private class
    """
    node_text = doc.get_node_text(node)
    # Check if text contains "private class" or "protected class"
    return ("private class" in node_text or "protected class" in node_text)


def _find_kotlin_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find KDoc at the start of Kotlin function body.

    In Kotlin, KDoc is documentation that appears at the start of the body.
    It's a multiline_comment starting with /** and should be preserved.

    Args:
        body_node: Function body node (function_body or block)
        doc: Tree-sitter document

    Returns:
        KDoc node if found, None otherwise
    """
    # Handle function_body wrapper
    actual_body = body_node
    if body_node.type == "function_body":
        if body_node.children:
            actual_body = body_node.children[0]

    # Look for block node
    if actual_body.type != "block":
        return None

    # Check for KDoc as first content inside block
    for child in actual_body.children:
        # Skip opening brace
        if doc.get_node_text(child) == "{":
            continue

        # Check if it's a KDoc comment
        if child.type in ("multiline_comment", "block_comment"):
            comment_text = doc.get_node_text(child)
            if comment_text.startswith("/**"):
                return child

        # If first non-brace, non-comment element, stop looking
        if child.type not in ("multiline_comment", "block_comment", "line_comment"):
            break

    return None


# --- Kotlin Code Descriptor ---

KOTLIN_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="kotlin",
    profiles=[
        # === Classes ===
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        # === Objects ===
        # Kotlin-specific: singleton objects and companion objects
        ElementProfile(
            name="object",
            query="(object_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        # === Functions ===
        # Top-level function declarations (not inside class/object)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_kotlin,
            additional_check=lambda node, doc: not _is_inside_class(node),
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        # === Methods ===
        # Functions inside classes/objects
        ElementProfile(
            name="method",
            query="(function_declaration) @element",
            is_public=_is_public_kotlin,
            additional_check=lambda node, doc: _is_inside_class(node),
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        # === Properties ===
        # Kotlin properties (val/var/const val) - both top-level and class members
        ElementProfile(
            name="property",
            query="(property_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        # === Secondary Constructors ===
        # Constructors inside classes
        ElementProfile(
            name="constructor",
            query="(secondary_constructor) @element",
            is_public=_is_public_kotlin,
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        # === Init Blocks ===
        # Anonymous initializers (init { ... })
        ElementProfile(
            name="init",
            query="(anonymous_initializer) @element",
            is_public=_is_public_kotlin,
            has_body=True,
        ),

        # === Getters ===
        ElementProfile(
            name="getter",
            query="(getter) @element",
            is_public=_is_public_kotlin,
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        # === Setters ===
        ElementProfile(
            name="setter",
            query="(setter) @element",
            is_public=_is_public_kotlin,
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        # === Misparsed Classes ===
        # Tree-sitter sometimes misparsed classes with multiple annotations as infix_expression
        # Requires both additional_check (to filter) and custom is_public (text-based)
        ElementProfile(
            name="class",
            query="(infix_expression) @element",
            is_public=_is_public_misparsed_class,
            additional_check=lambda node, doc: _is_misparsed_class(node, doc),
        ),
    ],

    decorator_types={"annotation"},
    comment_types={"line_comment", "block_comment", "multiline_comment"},
    name_extractor=_extract_name,
)


__all__ = ["KOTLIN_CODE_DESCRIPTOR"]
