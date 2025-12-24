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

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of JavaScript element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # Special handling for variable_declaration and lexical_declaration
    if node.type in ("variable_declaration", "lexical_declaration"):
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


def _is_exported_via_default(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if element is exported via 'export default Name'.

    For classes and functions that are declared separately and then exported.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is exported via default export
    """
    # Extract element name
    name = _extract_name(node, doc)
    if not name:
        return False

    # Search for export default statements in the document
    root = doc.root_node
    for child in root.children:
        if child.type == "export_statement":
            # Check if this is 'export default Name'
            export_text = doc.get_node_text(child).strip()
            if f"export default {name}" in export_text:
                return True

    return False


def _is_public_top_level(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if top-level JavaScript element is public.

    Top-level elements are public if:
    1. They have 'export' keyword in declaration
    2. They are exported via 'export default Name'

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is exported (public)
    """
    # Check direct export
    if _has_export_keyword(node, doc):
        return True

    # Check export via default
    return _is_exported_via_default(node, doc)


def _is_public_class_member(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if class member (method/field) is public.

    In JavaScript, class members are public by default.
    Private members are identified by:
    1. # prefix (modern private fields/methods): #privateMethod, #privateField
    2. _ prefix (convention-based protected/private): _protectedMethod

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private/protected
    """
    # Check for private_property_identifier in children (# prefix)
    for child in node.children:
        if child.type == "private_property_identifier":
            return False

        # Check for _ prefix in identifier names (convention-based private)
        if child.type == "property_identifier":
            name = doc.get_node_text(child)
            if name.startswith("_"):
                return False

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


def _has_arrow_function_body(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if variable declaration contains arrow function with statement_block body.

    Arrow functions can have:
    - Expression body: const f = () => "value"  (no braces, single expression)
    - Block body: const f = () => { return "value"; }  (with braces)

    We only care about block bodies for function body optimization.

    Args:
        node: variable_declaration or lexical_declaration node
        doc: Tree-sitter document

    Returns:
        True if contains arrow function with block body
    """
    # Find variable_declarator child
    for child in node.children:
        if child.type == "variable_declarator":
            # Find arrow_function child
            for grandchild in child.children:
                if grandchild.type == "arrow_function":
                    # Check if arrow function has statement_block body
                    for arrow_child in grandchild.children:
                        if arrow_child.type == "statement_block":
                            return True
    return False


def _find_arrow_function_body(node: Node) -> Optional[Node]:
    """
    Extract arrow function body node from variable declaration.

    Args:
        node: variable_declaration or lexical_declaration node

    Returns:
        statement_block node if found, None otherwise
    """
    # Navigate: variable_declaration -> variable_declarator -> arrow_function -> statement_block
    for child in node.children:
        if child.type == "variable_declarator":
            for grandchild in child.children:
                if grandchild.type == "arrow_function":
                    for arrow_child in grandchild.children:
                        if arrow_child.type == "statement_block":
                            return arrow_child
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
            self._original_node = start_node
            # Copy other attributes for compatibility
            for attr in ['children', 'text']:
                if hasattr(start_node, attr):
                    setattr(self, attr, getattr(start_node, attr))

        def child_by_field_name(self, name: str):
            """Delegate to original node."""
            return self._original_node.child_by_field_name(name)

    return ExtendedRangeNode(original_node, semicolon_node)


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
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_declaration", "class_body"}
            ),
            has_body=True,
            body_query='(function_declaration body: (statement_block) @body)',
            docstring_extractor=_find_javascript_docstring,
        ),

        # === Arrow Functions ===
        # Arrow functions declared as variables: const f = () => { }
        # Need to handle both lexical_declaration (const/let) and variable_declaration (var)
        ElementProfile(
            name="arrow_function",  # Separate name for arrow functions
            query="(lexical_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=_has_arrow_function_body,  # Only arrow functions with block body
            has_body=True,
            body_resolver=_find_arrow_function_body,  # Custom resolver for nested structure
            docstring_extractor=_find_javascript_docstring,
        ),

        ElementProfile(
            name="arrow_function",  # Separate name for arrow functions
            query="(variable_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=_has_arrow_function_body,  # Only arrow functions with block body
            has_body=True,
            body_resolver=_find_arrow_function_body,  # Custom resolver for nested structure
            docstring_extractor=_find_javascript_docstring,
        ),

        # === Methods ===
        # Methods inside classes (supports # prefix for private methods)
        ElementProfile(
            name="method",
            query="(method_definition) @element",
            is_public=_is_public_class_member,
            has_body=True,
            body_query='(method_definition body: (statement_block) @body)',
            docstring_extractor=_find_javascript_docstring,
        ),

        # === Class Fields ===
        # Public and private class fields (# prefix)
        ElementProfile(
            name="field",
            query="(field_definition) @element",
            is_public=_is_public_class_member,
        ),

        # === Variables ===
        # Top-level const/let/var declarations (excluding arrow functions and function-local variables)
        ElementProfile(
            name="variable",
            query="(variable_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: (
                not is_inside_container(node, {"class_declaration", "class_body"}) and
                not is_inside_container(node, {
                    "function_declaration", "method_definition", "arrow_function",
                    "function_expression", "generator_function"
                }) and
                not _has_arrow_function_body(node, doc)
            ),
        ),

        ElementProfile(
            name="variable",
            query="(lexical_declaration) @element",
            is_public=_is_public_top_level,
            additional_check=lambda node, doc: (
                not is_inside_container(node, {"class_declaration", "class_body"}) and
                not is_inside_container(node, {
                    "function_declaration", "method_definition", "arrow_function",
                    "function_expression", "generator_function"
                }) and
                not _has_arrow_function_body(node, doc)
            ),
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
    extend_element_range=_extend_range_for_semicolon,
)


__all__ = ["JAVASCRIPT_CODE_DESCRIPTOR"]
