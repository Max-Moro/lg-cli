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

from typing import List, Optional

from ...shared import ElementProfile, InheritMode, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Kotlin element from node.
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
    """
    node_text = doc.get_node_text(node)
    # Check if text contains "private class" or "protected class"
    return "private class" in node_text or "protected class" in node_text


def _resolve_kotlin_body(element_node: Node) -> Optional[Node]:
    """
    Resolve Kotlin function/getter/setter body to actual block node.

    In Kotlin AST, function body is wrapped:
    - function_declaration -> function_body -> block
    - getter -> function_body -> block
    - setter -> function_body -> block
    - secondary_constructor -> function_body -> block
    """
    # Find function_body child
    for child in element_node.children:
        if child.type == "function_body":
            # Find block inside function_body
            for grandchild in child.children:
                if grandchild.type == "block":
                    return grandchild
    return None


def _resolve_lambda_body(lambda_node: Node) -> Optional[Node]:
    """
    Resolve lambda_literal body to itself (lambda has special structure).

    Lambda structure: { [params ->] body_content }
    Unlike functions, lambda doesn't have a separate block node.
    Body content is directly inside lambda_literal.
    """
    return lambda_node


def _find_kotlin_decorators(node: Node, _doc: TreeSitterDocument, decorator_types: set) -> List[Node]:
    """
    Find Kotlin annotations using language-specific AST structure.

    Kotlin has two annotation placement patterns:
    1. Inside 'modifiers' node (normal classes):
       class_declaration -> modifiers -> annotation
    2. Nested 'annotated_expression' (misparsed private classes):
       annotated_expression -> annotation
         annotated_expression -> annotation
           infix_expression (our node)
    """
    decorators: List[Node] = []

    # Strategy 1: Walk up through annotated_expression wrappers
    current = node.parent
    while current and current.type == "annotated_expression":
        for child in current.children:
            if child.type in decorator_types:
                # Insert at beginning to preserve order (outermost first)
                decorators.insert(0, child)
        current = current.parent

    # Strategy 2: Look for modifiers child (normal classes/functions)
    for child in node.children:
        if child.type == "modifiers":
            # Extract decorators from modifiers node
            for modifier_child in child.children:
                if modifier_child.type in decorator_types:
                    if modifier_child not in decorators:
                        decorators.append(modifier_child)
            break

    return decorators


def _compute_kotlin_lambda_body_range(lambda_node: Node, doc: TreeSitterDocument) -> tuple[int, int]:
    """
    Compute strippable range for Kotlin lambda_literal.

    Lambda structure: { [params ->] body_content }
    Need to find content after '->' (if present) or after '{', and before '}'.
    """
    # Find opening and closing braces and arrow
    opening_brace = None
    closing_brace = None
    arrow = None

    for child in lambda_node.children:
        child_text = doc.get_node_text(child)
        if child_text == "{":
            opening_brace = child
        elif child_text == "}":
            closing_brace = child
        elif child_text == "->":
            arrow = child

    # Start position: after '->' if present, otherwise after '{'
    if arrow:
        start_byte = arrow.end_byte
    elif opening_brace:
        start_byte = opening_brace.end_byte
    else:
        start_byte = lambda_node.start_byte

    # End position: before '}'
    if closing_brace:
        end_byte = closing_brace.start_byte
    else:
        end_byte = lambda_node.end_byte

    return start_byte, end_byte


def _find_kotlin_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find KDoc at the start of Kotlin function body.

    In Kotlin, KDoc is documentation that appears at the start of the body.
    It's a multiline_comment starting with /** and should be preserved.
    """
    # Body should be block at this point (after body_resolver)
    if body_node.type != "block":
        return None

    # Check for KDoc as first content inside block
    for child in body_node.children:
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


KOTLIN_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="kotlin",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        ElementProfile(
            name="object",
            query="(object_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_kotlin,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_declaration", "class_body", "object_declaration"}
            ),
            has_body=True,
            body_resolver=_resolve_kotlin_body,
            docstring_extractor=_find_kotlin_docstring,
        ),

        ElementProfile(
            name="method",
            inherit_previous=InheritMode.NEGATE_CHECK,
        ),

        ElementProfile(
            name="getter",
            query="(getter) @element",
            is_public=_is_public_kotlin,
            has_body=True,
            body_resolver=_resolve_kotlin_body,
            docstring_extractor=_find_kotlin_docstring,
        ),

        ElementProfile(
            name="setter",
            query="(setter) @element",
            inherit_previous=InheritMode.INHERIT,
        ),

        ElementProfile(
            name="property",
            query="(property_declaration) @element",
            is_public=_is_public_kotlin,
        ),

        # Note: secondary_constructor directly has 'block' child (no function_body wrapper)
        ElementProfile(
            name="constructor",
            query="(secondary_constructor) @element",
            is_public=_is_public_kotlin,
            has_body=True,
            docstring_extractor=_find_kotlin_docstring,
        ),

        ElementProfile(
            name="init",
            query="(anonymous_initializer) @element",
            is_public=_is_public_kotlin,
            has_body=True,
        ),

        # Note: lambda_literal has special structure - body content is directly inside
        ElementProfile(
            name="lambda",
            query="(lambda_literal) @element",
            is_public=None,  # Lambdas don't have visibility - determined by containing declaration
            has_body=True,
            body_resolver=_resolve_lambda_body,  # Returns lambda itself (for body node resolution)
            body_range_computer=_compute_kotlin_lambda_body_range,  # Custom range computation
        ),

        # Tree-sitter sometimes misparsed classes with multiple annotations as infix_expression
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
    decorator_finder=_find_kotlin_decorators,  # Kotlin-specific decorator finding
)


__all__ = ["KOTLIN_CODE_DESCRIPTOR"]
