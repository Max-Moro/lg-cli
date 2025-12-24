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

from ...shared import ElementProfile, LanguageCodeDescriptor
from ...tree_sitter_support import Node, TreeSitterDocument


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


def _is_inside_namespace(node: Node) -> bool:
    """Check if node is inside namespace (internal_module)."""
    current = node.parent
    while current:
        if current.type == "internal_module":
            return True
        if current.type in ("program", "source_file"):
            return False
        current = current.parent
    return False


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of TypeScript element from node.

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

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Modifier text ("private", "protected", "public") or None
    """
    for child in node.children:
        if child.type == "accessibility_modifier":
            return doc.get_node_text(child).strip()
    return None


def _has_export_keyword(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node has 'export' keyword directly before it.

    For namespace members and top-level declarations.

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
    Determine if top-level TypeScript element is public.

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

    Class members use visibility modifiers:
    - private modifier = private
    - protected modifier = private (protected)
    - public modifier or no modifier = public

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public
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

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is exported
    """
    return _has_export_keyword(node, doc)


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


def _find_typescript_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring (JSDoc comment) at the start of function body.

    In TypeScript, docstrings are typically handled via JSDoc comments
    which appear before the function, not inside the body.
    This searches for comment nodes at the start of the body.

    Args:
        body_node: Function body node (statement_block)
        doc: Tree-sitter document

    Returns:
        Comment node if found, None otherwise
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


def _extend_range_for_semicolon(node: Node, element_type: str, doc: TreeSitterDocument) -> Node:
    """
    Extend element range to include trailing semicolon.

    For fields and variables, includes trailing semicolon in element range
    to ensure proper grouping of adjacent elements.

    Args:
        node: Element node
        element_type: Type of element
        doc: Tree-sitter document

    Returns:
        Node with potentially extended range
    """
    # Only extend for specific element types
    if element_type not in ("field", "variable"):
        return node

    # Check if there's a semicolon right after this node
    parent = node.parent
    if not parent:
        return node

    # Find position of this node among siblings
    siblings = parent.children
    node_index = None
    for i, sibling in enumerate(siblings):
        if sibling == node:
            node_index = i
            break

    if node_index is None:
        return node

    # Check if next sibling is a semicolon
    if node_index + 1 < len(siblings):
        next_sibling = siblings[node_index + 1]
        if next_sibling.type == ";" or doc.get_node_text(next_sibling).strip() == ";":
            # Create synthetic node with extended range
            return _create_extended_range_node(node, next_sibling)

    return node


def _create_extended_range_node(original_node: Node, semicolon_node: Node) -> Node:
    """
    Create synthetic node with extended range.

    Args:
        original_node: Original element node
        semicolon_node: Semicolon node to include

    Returns:
        Synthetic node with extended range
    """
    class ExtendedRangeNode:
        """Duck-typed node with extended byte range."""
        def __init__(self, start_node: Node, end_node: Node):
            self.start_byte = start_node.start_byte
            self.end_byte = end_node.end_byte
            self.start_point = start_node.start_point
            self.end_point = end_node.end_point
            self.type = start_node.type
            self.parent = start_node.parent
            # Copy other attributes for compatibility
            for attr in ['children', 'text']:
                if hasattr(start_node, attr):
                    setattr(self, attr, getattr(start_node, attr))

    return ExtendedRangeNode(original_node, semicolon_node)


# --- TypeScript Code Descriptor ---

TYPESCRIPT_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="typescript",
    profiles=[
        # === Classes ===
        ElementProfile(
            name="class",
            query="(class_declaration) @element",
            is_public=_is_public_top_level,
        ),

        # === Interfaces ===
        ElementProfile(
            name="interface",
            query="(interface_declaration) @element",
            is_public=_is_public_top_level,
        ),

        # === Type Aliases ===
        ElementProfile(
            name="type",
            query="(type_alias_declaration) @element",
            is_public=_is_public_top_level,
        ),

        # === Enums ===
        ElementProfile(
            name="enum",
            query="(enum_declaration) @element",
            is_public=_is_public_top_level,
        ),

        # === Namespaces ===
        ElementProfile(
            name="namespace",
            query="(internal_module) @element",
            is_public=_is_public_top_level,
        ),

        # === Functions ===
        # Top-level functions (not in class or namespace)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: not _is_inside_class(node) and not _is_inside_namespace(node),
            has_body=True,
            body_query='(function_declaration body: (statement_block) @body)',
            docstring_extractor=_find_typescript_docstring,
        ),

        # Functions inside namespace (must have explicit export to be public)
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_namespace_member,
            additional_check=lambda node, doc: _is_inside_namespace(node),
            has_body=True,
            body_query='(function_declaration body: (statement_block) @body)',
            docstring_extractor=_find_typescript_docstring,
        ),

        # Arrow functions
        ElementProfile(
            name="function",
            query="(arrow_function) @element",
            is_public=None,  # Arrow functions visibility determined by variable declaration
            has_body=True,
            # Arrow functions can have expression or statement_block body
            # No specific body_query needed - _find_body_node will find it
            docstring_extractor=_find_typescript_docstring,
        ),

        # === Methods ===
        # Methods inside classes use visibility modifiers
        ElementProfile(
            name="method",
            query="(method_definition) @element",
            is_public=_is_public_class_member,
            has_body=True,
            body_query='(method_definition body: (statement_block) @body)',
            docstring_extractor=_find_typescript_docstring,
        ),

        # === Class Fields ===
        # Properties inside classes
        ElementProfile(
            name="field",
            query="(public_field_definition) @element",
            is_public=_is_public_class_member,
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

    decorator_types={"decorator", "decorator_expression"},
    comment_types={"comment", "line_comment", "block_comment"},
    name_extractor=_extract_name,
    extend_element_range=_extend_range_for_semicolon,
)


__all__ = ["TYPESCRIPT_CODE_DESCRIPTOR"]
