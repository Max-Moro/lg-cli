"""
JavaScript code profiles for declarative element collection.

Describes all code element types in JavaScript:
- Classes
- Functions (top-level)
- Methods (inside classes)
- Variables (module-level)

JavaScript uses the 'export' keyword for public API.
Unlike TypeScript, there are no visibility modifiers (private/protected/public).
Top-level declarations are public only if they have 'export' keyword.
Class members are always considered public (no visibility modifiers in standard JS).
"""

from __future__ import annotations

from typing import Optional

from ..optimizations.shared import ElementProfile, LanguageCodeDescriptor
from ..tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_inside_class(node: Node) -> bool:
    """Check if node is inside class definition."""
    current = node.parent
    while current:
        if current.type in ("class_declaration", "class_body"):
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of JavaScript element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
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
        if child.type in ("identifier", "property_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _has_export_keyword(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node has 'export' keyword directly before it.

    For top-level declarations.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is exported
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
    Determine if top-level JavaScript element is public.

    Top-level elements are public only if they have 'export' keyword.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is exported (public)
    """
    return _has_export_keyword(node, doc)


def _is_public_class_member(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if class member (method/field) is public.

    In JavaScript, class members don't have visibility modifiers (like TypeScript).
    All members are public by default (unless prefixed with # for private fields,
    but that's a syntax detail handled at tree-sitter level).

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public (always True in JavaScript)
    """
    # JavaScript has no visibility modifiers, all members are public
    return True


def _is_side_effect_import(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if import is side-effect only (must be preserved).

    Side-effect imports: import './module' (no destructuring, no 'from')
    These can modify global state and must not be removed.

    Args:
        node: Tree-sitter node of import statement
        doc: Tree-sitter document

    Returns:
        True if import is side-effect import
    """
    import_text = doc.get_node_text(node)
    # Side-effect if no 'from', no '{', no '* as'
    return ("from" not in import_text) and ("{" not in import_text) and ("* as" not in import_text)


def _find_javascript_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (JSDoc comment) at the start of function body.

    In JavaScript, docstrings are typically handled via JSDoc comments
    which appear before the function, not inside the body.
    This searches for comment nodes at the start of the body.

    Args:
        body_node: Function body node (statement_block)
        doc: Tree-sitter document

    Returns:
        Comment node if found, None otherwise
    """
    # JavaScript docstrings are usually before the function, not in the body
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


# --- JavaScript Code Descriptor ---

JAVASCRIPT_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="javascript",
    profiles=[
        # === Classes ===
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_top_level,
        ),

        # === Functions ===
        # Top-level functions (not in class)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: not _is_inside_class(node),
            has_body=True,
            body_query='(function_declaration body: (statement_block) @body)',
            docstring_extractor=_find_javascript_docstring,
        ),

        # === Methods ===
        # Methods inside classes (no visibility modifiers in JavaScript)
        ElementProfile(
            name="method",
            query="(method_definition) @element",
            is_public=_is_public_class_member,
            has_body=True,
            body_query='(method_definition body: (statement_block) @body)',
            docstring_extractor=_find_javascript_docstring,
        ),

        # === Variables ===
        # Top-level const/let/var declarations
        ElementProfile(
            name="variable",
            query="(variable_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: not _is_inside_class(node),
        ),

        # === Imports ===
        # Collect non-side-effect imports for removal
        # Side-effect imports are preserved by default (not in this profile)
        ElementProfile(
            name="import",
            query="(import_statement) @element",
            is_public=lambda node, doc: _is_side_effect_import(node, doc),  # side-effect = public (keep)
            additional_check=lambda node, doc: not _is_side_effect_import(node, doc),  # filter to regular imports
        ),
    ],

    decorator_types=set(),
    comment_types={"comment", "line_comment", "block_comment"},
    name_extractor=_extract_name,
)


__all__ = ["JAVASCRIPT_CODE_DESCRIPTOR"]
