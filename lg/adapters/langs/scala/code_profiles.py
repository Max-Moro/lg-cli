"""
Scala code profiles for declarative element collection.

Describes all code element types in Scala:
- Classes (regular)
- Case classes
- Traits
- Objects (singletons)
- Functions (top-level)
- Methods (inside classes/traits/objects)
- Variables/Properties (val/var at various levels)
- Fields (class members)

Scala uses explicit visibility modifiers for public API determination:
- private = private
- protected = protected (treated as private for public API)
- internal = module-level (treated as private for public API)
- No modifier = public (default)
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor
from ...tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_inside_class(node: Node) -> bool:
    """
    Check if node is inside class, object, or trait definition.

    Args:
        node: Tree-sitter node

    Returns:
        True if node is inside a class/object/trait
    """
    current = node.parent
    while current:
        if current.type in ("class_definition", "object_definition", "trait_definition", "template_body"):
            return True
        if current.type == "compilation_unit":
            break
        current = current.parent
    return False


def _is_case_class(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if a class definition is a case class.

    Case classes have 'case' modifier in Scala.

    Args:
        node: class_definition node
        doc: Tree-sitter document

    Returns:
        True if it's a case class
    """
    node_text = doc.get_node_text(node)
    return "case class" in node_text[:50]


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Scala element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # Special handling for val/var definitions - name is in pattern field
    if node.type in ("val_definition", "var_definition", "val_declaration", "var_declaration"):
        pattern_node = node.child_by_field_name("pattern")
        if pattern_node and pattern_node.type == "identifier":
            return doc.get_node_text(pattern_node)

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
    Extract visibility modifier from Scala node.

    Scala visibility modifiers: private, protected, public.
    No modifier means public (default).

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Modifier text ("private", "protected", "public") or None
    """
    for child in node.children:
        if child.type == "modifiers":
            for modifier_child in child.children:
                if modifier_child.type == "access_modifier":
                    return doc.get_node_text(modifier_child).strip()
    return None


def _is_public_scala(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Scala element is public based on visibility modifiers.

    Scala rules:
    - private = private
    - protected = protected (treated as private for public API)
    - No modifier = public (default)

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    modifier = _get_visibility_modifier(node, doc)

    # private and protected = private
    if modifier in ("private", "protected"):
        return False

    # No modifier or public = public (default in Scala)
    return True


def _find_scala_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find ScalaDoc at the start of Scala function body.

    In Scala, ScalaDoc is documentation that appears at the start of the body.
    It's a block_comment or multiline_comment starting with /** and should be preserved.

    Args:
        body_node: Function body node (block or function_body)
        doc: Tree-sitter document

    Returns:
        ScalaDoc node if found, None otherwise
    """
    # Handle function_body wrapper - get actual block inside
    actual_body = body_node
    if body_node.type == "function_body":
        if body_node.children:
            actual_body = body_node.children[0]

    # Look for block node
    if actual_body.type != "block":
        return None

    # Check for ScalaDoc as first content inside block
    for child in actual_body.children:
        # Skip opening brace
        if doc.get_node_text(child) == "{":
            continue

        # Check if it's a ScalaDoc comment
        if child.type in ("multiline_comment", "block_comment"):
            comment_text = doc.get_node_text(child)
            if comment_text.startswith("/**"):
                return child

        # If first non-brace, non-comment element, stop looking
        if child.type not in ("multiline_comment", "block_comment", "line_comment"):
            break

    return None


# --- Scala Code Descriptor ---

SCALA_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="scala",
    profiles=[
        # === Classes ===
        # Regular classes (non-case)
        ElementProfile(
            name="class",
            query="(class_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_case_class(node, doc),
        ),

        # === Case Classes ===
        ElementProfile(
            name="case_class",
            query="(class_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_case_class(node, doc),
        ),

        # === Traits ===
        ElementProfile(
            name="trait",
            query="(trait_definition) @element",
            is_public=_is_public_scala,
        ),

        # === Objects ===
        # Singletons and companion objects
        ElementProfile(
            name="object",
            query="(object_definition) @element",
            is_public=_is_public_scala,
        ),

        # === Type aliases ===
        ElementProfile(
            name="type",
            query="(type_definition) @element",
            is_public=_is_public_scala,
        ),

        # === Functions and Methods ===
        # Top-level functions with body (function_definition)
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_inside_class(node),
            has_body=True,
            docstring_extractor=_find_scala_docstring,
        ),

        # Methods inside classes/traits/objects (function_definition)
        ElementProfile(
            name="method",
            query="(function_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_inside_class(node),
            has_body=True,
            docstring_extractor=_find_scala_docstring,
        ),

        # Abstract function declarations (function_declaration - no body)
        # Top-level abstract functions
        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_inside_class(node),
        ),

        # Abstract methods inside classes/traits
        ElementProfile(
            name="method",
            query="(function_declaration) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_inside_class(node),
        ),

        # === Module-level Variables ===
        # val at module level (not inside classes)
        ElementProfile(
            name="variable",
            query="(val_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_inside_class(node),
        ),

        # var at module level (not inside classes)
        ElementProfile(
            name="variable",
            query="(var_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_inside_class(node),
        ),

        # === Class Fields ===
        # val properties inside classes
        ElementProfile(
            name="field",
            query="(val_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_inside_class(node),
        ),

        # var properties inside classes
        ElementProfile(
            name="field",
            query="(var_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_inside_class(node),
        ),
    ],

    decorator_types={"annotation"},
    comment_types={"comment", "block_comment", "multiline_comment"},
    name_extractor=_extract_name,
)


__all__ = ["SCALA_CODE_DESCRIPTOR"]
