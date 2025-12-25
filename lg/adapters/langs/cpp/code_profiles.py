"""
C++ code profiles for declarative element collection.

Describes all code element types in C++:
- Classes
- Structs
- Unions
- Enums
- Functions (top-level)
- Methods (inside classes/structs/unions)
- Fields (class/struct member variables)
- Namespaces

C++ uses visibility modifiers (public, private, protected) for access control:
- 'public' access specifier = public
- 'private' access specifier = private
- 'protected' access specifier = protected
- No access specifier: default is private for class, public for struct
- Namespace members default to internal unless exported
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, InheritMode, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _get_access_specifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Find the access specifier (public, private, protected) for a class/struct member.

    For nested classes inside field_declaration, checks parent's siblings.
    For regular members, checks parent's children.
    """
    # For nested classes inside field_declaration
    if node.parent and node.parent.type == "field_declaration":
        if node.parent.parent and node.parent.parent.type == "field_declaration_list":
            # This is a nested class - check siblings of field_declaration
            return _search_access_specifier_in_siblings(
                node.parent, node.parent.parent.children, doc
            )

    # For regular members, check current parent's children
    if not node.parent:
        return None

    return _search_access_specifier_in_siblings(node, node.parent.children, doc)


def _search_access_specifier_in_siblings(
    target_node: Node, siblings: list, doc: TreeSitterDocument
) -> Optional[str]:
    """
    Search for access specifier among siblings before target node.
    """
    current_access = None

    for sibling in siblings:
        if sibling == target_node:
            return current_access

        if sibling.type == "access_specifier":
            specifier_text = doc.get_node_text(sibling).strip()
            if specifier_text.startswith("public"):
                current_access = "public"
            elif specifier_text.startswith("private"):
                current_access = "private"
            elif specifier_text.startswith("protected"):
                current_access = "protected"

    return current_access


def _get_parent_class_or_struct_type(node: Node) -> Optional[str]:
    """
    Find the type of parent class or struct (class_specifier or struct_specifier).
    """
    current = node.parent
    while current:
        if current.type == "class_specifier":
            return "class"
        elif current.type == "struct_specifier":
            return "struct"
        elif current.type == "union_specifier":
            return "union"
        current = current.parent
    return None


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of C++ element from node.
    """
    # For qualified identifiers (e.g., namespace::class::method), get the last identifier
    if node.type == "qualified_identifier":
        for child in reversed(node.children):
            if child.type == "identifier":
                return doc.get_node_text(child)

    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _is_public_cpp(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if C++ element is public based on access specifiers.

    Rules:
    - Members with explicit 'public' modifier = public
    - Members with explicit 'private' modifier = private
    - Members with explicit 'protected' modifier = private
    - No explicit modifier in class = private (default for class)
    - No explicit modifier in struct = public (default for struct)
    - Top-level functions/classes = public (unless static or in anonymous namespace)
    """
    if is_inside_container(
        node,
        {"class_specifier", "struct_specifier", "union_specifier"},
        boundary_types={"namespace_definition", "translation_unit"}
    ):
        access = _get_access_specifier(node, doc)

        if access == "public":
            return True
        elif access in ("private", "protected"):
            return False

        # No explicit modifier - default is private for class, public for struct/union
        parent_type = _get_parent_class_or_struct_type(node)
        if parent_type == "class":
            return False
        else:
            return True

    if _has_static_specifier(node, doc):
        return False
    if _in_anonymous_namespace(node):
        return False

    return True


def _has_static_specifier(node: Node, doc: TreeSitterDocument) -> bool:
    """Check if node has static storage class specifier."""
    for child in node.children:
        if child.type == "storage_class_specifier":
            if "static" in doc.get_node_text(child):
                return True
    return False


def _in_anonymous_namespace(node: Node) -> bool:
    """Check if node is inside an anonymous namespace."""
    current = node.parent
    while current:
        if current.type == "namespace_definition":
            has_name = False
            for child in current.children:
                if child.type == "namespace_identifier":
                    has_name = True
                    break
            if not has_name:
                return True
        current = current.parent
    return False


def _find_cpp_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (comment) at the start of function body.

    In C++, docstrings are typically handled via comments (/* */ or //)
    which appear before the function, not inside the body.
    This searches for comment nodes at the start of the body.
    """
    if not body_node or body_node.type != "compound_statement":
        return None

    for child in body_node.children:
        if child.type == "comment":
            return child
        if child.type not in ("newline", "\n", " ", "\t"):
            break

    return None


CPP_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="cpp",
    profiles=[
        ElementProfile(
            name="namespace",
            query="(namespace_definition) @element",
        ),

        ElementProfile(
            name="class",
            query="(class_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),

        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),

        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),

        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),

        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
            has_body=True,
            docstring_extractor=_find_cpp_docstring,
        ),

        ElementProfile(
            name="method",
            inherit_previous=InheritMode.NEGATE_CHECK,
        ),

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),

        ElementProfile(
            name="variable",
            query="(declaration) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"class_specifier", "struct_specifier", "union_specifier"},
                boundary_types={"namespace_definition", "translation_unit"}
            ),
        ),
    ],

    decorator_types=set(),
    comment_types={"comment"},
    name_extractor=_extract_name,
)


__all__ = ["CPP_CODE_DESCRIPTOR"]
