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

from ..optimizations.shared import ElementProfile, LanguageCodeDescriptor
from ..tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_inside_class_or_struct(node: Node) -> bool:
    """Check if node is inside class, struct, or union definition."""
    current = node.parent
    while current:
        if current.type in ("class_specifier", "struct_specifier", "union_specifier"):
            return True
        # Stop at namespace or translation unit boundary
        if current.type in ("namespace_definition", "translation_unit"):
            return False
        current = current.parent
    return False


def _is_inside_namespace(node: Node) -> bool:
    """Check if node is inside namespace definition."""
    current = node.parent
    while current:
        if current.type == "namespace_definition":
            return True
        if current.type == "translation_unit":
            return False
        current = current.parent
    return False


def _get_access_specifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Find the access specifier (public, private, protected) for a class/struct member.

    For nested classes inside field_declaration, checks parent's siblings.
    For regular members, checks parent's children.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Access specifier text ("public", "private", "protected") or None
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

    Args:
        target_node: The node we're looking for access specifier for
        siblings: List of sibling nodes to search
        doc: Tree-sitter document

    Returns:
        Access specifier text or None if not found
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

    Args:
        node: Tree-sitter node to analyze

    Returns:
        "class" or "struct" or None
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

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # For qualified identifiers (e.g., namespace::class::method)
    if node.type == "qualified_identifier":
        # Get the last identifier in the chain
        for child in reversed(node.children):
            if child.type == "identifier":
                return doc.get_node_text(child)

    # Search for child node with name
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
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

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    # For class/struct members
    if _is_inside_class_or_struct(node):
        access = _get_access_specifier(node, doc)

        # Explicit access specifier takes precedence
        if access == "public":
            return True
        elif access in ("private", "protected"):
            return False

        # No explicit modifier - use default based on parent type
        parent_type = _get_parent_class_or_struct_type(node)
        if parent_type == "class":
            return False  # Default for class is private
        else:
            return True   # Default for struct/union is public

    # For top-level elements (functions, classes, etc.)
    # Top-level is public unless static or in anonymous namespace
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
            # Check if namespace has a name
            has_name = False
            for child in current.children:
                if child.type == "namespace_identifier":
                    has_name = True
                    break
            if not has_name:
                return True  # Anonymous namespace
        current = current.parent
    return False


def _find_cpp_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (comment) at the start of function body.

    In C++, docstrings are typically handled via comments (/* */ or //)
    which appear before the function, not inside the body.
    This searches for comment nodes at the start of the body.

    Args:
        body_node: Function body node (compound_statement)
        doc: Tree-sitter document

    Returns:
        Comment node if found, None otherwise
    """
    if not body_node or body_node.type != "compound_statement":
        return None

    for child in body_node.children:
        if child.type == "comment":
            return child
        # First non-whitespace that's not a comment, stop
        if child.type not in ("newline", "\n", " ", "\t"):
            break

    return None


# --- C++ Code Descriptor ---

CPP_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="cpp",
    profiles=[
        # === Namespaces ===
        ElementProfile(
            name="namespace",
            query="(namespace_definition) @element",
        ),

        # === Classes ===
        ElementProfile(
            name="class",
            query="(class_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not _is_inside_class_or_struct(node),
        ),

        # === Structs ===
        ElementProfile(
            name="struct",
            query="(struct_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not _is_inside_class_or_struct(node),
        ),

        # === Unions ===
        ElementProfile(
            name="union",
            query="(union_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not _is_inside_class_or_struct(node),
        ),

        # === Enums ===
        ElementProfile(
            name="enum",
            query="(enum_specifier) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not _is_inside_class_or_struct(node),
        ),

        # === Functions (top-level) ===
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: not _is_inside_class_or_struct(node),
            has_body=True,
            docstring_extractor=_find_cpp_docstring,
        ),

        # === Methods (inside classes/structs/unions) ===
        ElementProfile(
            name="method",
            query="(function_definition) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: _is_inside_class_or_struct(node),
            has_body=True,
            docstring_extractor=_find_cpp_docstring,
        ),

        # === Class/Struct Fields ===
        # Only field_declaration inside field_declaration_list (not standalone declarations)
        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            is_public=_is_public_cpp,
            additional_check=lambda node, doc: _is_inside_class_or_struct(node),
        ),
    ],

    decorator_types=set(),  # C++ doesn't have decorators
    comment_types={"comment"},  # C++ has single comment type
    name_extractor=_extract_name,
)


__all__ = ["CPP_CODE_DESCRIPTOR"]
