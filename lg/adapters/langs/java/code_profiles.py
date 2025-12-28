"""
Java code profiles for declarative element collection.

Describes all code element types in Java:
- Classes
- Interfaces
- Enums
- Annotation types
- Methods
- Constructors
- Fields
- Variables (top-level)

Java uses visibility modifiers (public, private, protected, package-private)
for determining public API status:
- public = public
- protected/private = private
- package-private (no modifier) = internal
- Interface members are implicitly public
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, InheritMode, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _is_interface_member(node: Node) -> bool:
    """
    Check if node is a member of an interface.

    In Java, interface members (methods and fields) are implicitly public.
    """
    current = node.parent
    while current:
        if current.type == "interface_declaration":
            return True
        # Stop at class boundaries
        if current.type in ("class_declaration", "enum_declaration"):
            return False
        # Stop at file boundaries
        if current.type in ("program", "source_file"):
            break
        current = current.parent
    return False


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Java element from node.
    """
    if node.type in ("field_declaration", "local_variable_declaration"):
        for child in node.children:
            if child.type == "variable_declarator":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    for child in node.children:
        if child.type == "identifier":
            return doc.get_node_text(child)

    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _get_visibility_modifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract visibility modifier from node.
    """
    for child in node.children:
        if child.type == "modifiers":
            modifier_text = doc.get_node_text(child)
            if "private" in modifier_text:
                return "private"
            elif "protected" in modifier_text:
                return "protected"
            elif "public" in modifier_text:
                return "public"
    return None


def _is_public_java(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Java element is public based on visibility modifiers.

    Rules:
    - 'private' modifier = private (not public)
    - 'protected' modifier = protected (not public)
    - 'public' modifier = public
    - No modifier = package-private (internal, not public)
    - Interface members with no modifier = implicitly public
    """
    modifier = _get_visibility_modifier(node, doc)

    if modifier in ("private", "protected"):
        return False

    if modifier == "public":
        return True

    if _is_interface_member(node):
        return True

    return False


def _find_java_docstring(body_node: Node, _doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (Javadoc comment) at the start of method/constructor body.

    In Java, docstrings are typically handled via Javadoc comments
    which appear before the method, not inside the body.
    This searches for comment nodes at the start of the body.
    """
    if not body_node or body_node.type not in ("block", "constructor_body"):
        return None

    for child in body_node.children:
        if child.type in ("line_comment", "block_comment"):
            return child
        if child.type not in ("newline", "\n", " ", "\t"):
            break

    return None


JAVA_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="java",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_java,
        ),

        ElementProfile(
            name="interface",
            query="(interface_declaration) @element",
            is_public=_is_public_java,
        ),

        ElementProfile(
            name="enum",
            query="(enum_declaration) @element",
            is_public=_is_public_java,
        ),

        ElementProfile(
            name="annotation",
            query="(annotation_type_declaration) @element",
            is_public=_is_public_java,
        ),

        ElementProfile(
            name="method",
            query="(method_declaration) @element",
            is_public=_is_public_java,
            has_body=True,
            docstring_extractor=_find_java_docstring,
        ),

        ElementProfile(
            name="constructor",
            query="(constructor_declaration) @element",
            inherit_previous=InheritMode.INHERIT,
        ),

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            is_public=_is_public_java,
            additional_check=lambda node, doc: is_inside_container(
                node, {
                    "class_declaration", "interface_declaration", "enum_declaration",
                    "class_body", "interface_body", "enum_body"
                }
            ),
        ),

        # Java tree-sitter may parse top-level as local_variable_declaration
        ElementProfile(
            name="variable",
            query="(local_variable_declaration) @element",
            is_public=_is_public_java,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"method_declaration", "constructor_declaration", "block", "constructor_body"},
                boundary_types={"class_body", "interface_body", "enum_body", "program", "source_file"}
            ),
        ),
    ],

    decorator_types={"annotation", "marker_annotation"},
    comment_types={"line_comment", "block_comment"},
    name_extractor=_extract_name,
)


__all__ = ["JAVA_CODE_DESCRIPTOR"]
