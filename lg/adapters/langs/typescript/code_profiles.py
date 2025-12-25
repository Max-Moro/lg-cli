"""
TypeScript code profiles for declarative element collection.

Describes all code element types in TypeScript:
- Classes
- Interfaces
- Type aliases
- Enums
- Namespaces
- Functions (top-level)
- Methods (inside classes)
- Fields (class members)
- Variables (module-level)

TypeScript uses both visibility modifiers (private/protected/public)
and export keyword for public API:
- Top-level declarations (class, function, interface, etc.): use export keyword
- Class members (methods, fields): use visibility modifiers
- Namespace members: use export keyword
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, InheritMode, LanguageCodeDescriptor, is_inside_container, compute_element_range_with_trailing
from ...tree_sitter_support import Node, TreeSitterDocument


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of TypeScript element from node.
    """
    # Special handling for variable_declaration
    if node.type == "variable_declaration":
        for child in node.children:
            if child.type == "variable_declarator":
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        return doc.get_node_text(grandchild)

    # Search for child node with function/class/method name
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _get_visibility_modifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract visibility modifier from node.
    """
    for child in node.children:
        if child.type == "accessibility_modifier":
            return doc.get_node_text(child).strip()
    return None


def _has_export_keyword(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node has 'export' keyword directly before it.

    For namespace members and top-level declarations.
    """
    node_text = doc.get_node_text(node).strip()

    # Check if text starts with export keyword
    if node_text.startswith("export "):
        return True

    # Check parent for export_statement
    if node.parent and node.parent.type == "export_statement":
        return True

    return False


def _is_public_top_level(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if top-level TypeScript element is public.

    Top-level elements are public only if they have 'export' keyword.
    """
    return _has_export_keyword(node, doc)


def _is_public_class_member(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if class member (method/field) is public.

    Class members use visibility modifiers:
    - private modifier = private
    - protected modifier = private (protected)
    - public modifier or no modifier = public
    """
    modifier = _get_visibility_modifier(node, doc)

    # private and protected = private
    if modifier in ("private", "protected"):
        return False

    # public or no modifier = public
    return True


def _is_public_namespace_member(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if namespace member is public.

    Namespace members must have explicit 'export' to be public.
    """
    return _has_export_keyword(node, doc)


def _is_side_effect_import(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if import is side-effect only (must be preserved).

    Side-effect imports: import './module' (no destructuring, no 'from')
    These can modify global state and must not be removed.
    """
    import_text = doc.get_node_text(node)
    # Side-effect if no 'from', no '{', no '* as'
    return ("from" not in import_text) and ("{" not in import_text) and ("* as" not in import_text)


def _find_typescript_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (JSDoc comment) at the start of function body.

    In TypeScript, docstrings are typically handled via JSDoc comments
    which appear before the function, not inside the body.
    This searches for comment nodes at the start of the body.
    """
    # TypeScript docstrings are usually before the function, not in the body
    # We check if there's a comment as first child
    if not body_node or body_node.type != "statement_block":
        return None

    for child in body_node.children:
        if child.type in ("comment", "line_comment", "block_comment"):
            return child
        # First statement/whitespace that's not a comment, stop
        if child.type not in ("newline", "\n", " ", "\t"):
            break

    return None


def _compute_element_range(node: Node, element_type: str, doc: TreeSitterDocument) -> Optional[tuple[int, int]]:
    """Compute adjusted element range to include trailing semicolon."""
    return compute_element_range_with_trailing(
        node, element_type, doc,
        element_types={"field", "variable"},
        trailing_chars={";"},
    )


TYPESCRIPT_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="typescript",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_top_level,
        ),

        ElementProfile(
            name="interface",
            query="(interface_declaration) @element",
            is_public=_is_public_top_level,
        ),

        ElementProfile(
            name="type",
            query="(type_alias_declaration) @element",
            is_public=_is_public_top_level,
        ),

        ElementProfile(
            name="enum",
            query="(enum_declaration) @element",
            is_public=_is_public_top_level,
        ),

        ElementProfile(
            name="namespace",
            query="(internal_module) @element",
            is_public=_is_public_top_level,
        ),

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: (
                not is_inside_container(node, {"class_declaration", "class_body"}) and
                not is_inside_container(node, {"internal_module"})
            ),
            has_body=True,
            body_query='(function_declaration body: (statement_block) @body)',
            docstring_extractor=_find_typescript_docstring,
        ),

        # Namespace members must have explicit export to be public
        ElementProfile(
            is_public=_is_public_namespace_member,
            additional_check=lambda node, doc: is_inside_container(node, {"internal_module"}),
            inherit_previous=InheritMode.INHERIT,
        ),

        # Arrow functions can have expression or statement_block body
        ElementProfile(
            name="function",
            query="(arrow_function) @element",
            is_public=None,  # Arrow functions visibility determined by variable declaration
            has_body=True,
            docstring_extractor=_find_typescript_docstring,
        ),

        ElementProfile(
            name="method",
            query="(method_definition) @element",
            is_public=_is_public_class_member,
            has_body=True,
            body_query='(method_definition body: (statement_block) @body)',
            docstring_extractor=_find_typescript_docstring,
        ),

        ElementProfile(
            name="field",
            query="(public_field_definition) @element",
            is_public=_is_public_class_member,
        ),

        ElementProfile(
            name="variable",
            query="(variable_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_declaration", "class_body"}
            ),
        ),

        # Side-effect imports are preserved by default (not in this profile)
        ElementProfile(
            name="import",
            query="(import_statement) @element",
            is_public=lambda node, doc: _is_side_effect_import(node, doc),  # side-effect = public (keep)
            additional_check=lambda node, doc: not _is_side_effect_import(node, doc),  # filter to regular imports
        ),
    ],

    decorator_types={"decorator", "decorator_expression"},
    comment_types={"comment", "line_comment", "block_comment"},
    name_extractor=_extract_name,
    compute_element_range=_compute_element_range,
)


__all__ = ["TYPESCRIPT_CODE_DESCRIPTOR"]
