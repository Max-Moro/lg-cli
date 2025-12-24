"""
Rust code profiles for declarative element collection.

Describes all code element types in Rust:
- Structs
- Enums
- Traits
- Impl blocks
- Functions (top-level)
- Methods (inside impl)
- Constants
- Static variables
- Modules
- Fields

Rust uses pub keyword for visibility with variants:
- pub - public
- pub(crate) - crate-level (internal, but part of crate's public API)
- pub(super) - parent module (protected, but part of module tree's public API)
- pub(self) - current module (private)
- no modifier - private

Trait methods inherit visibility from the trait.
Methods in trait impls are always public.
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container, compute_element_range_with_trailing
from ...tree_sitter_support import Node, TreeSitterDocument


# --- Helper functions ---


def _is_in_trait_impl(node: Node) -> bool:
    """Check if node is inside trait implementation (impl Trait for Type)."""
    current = node.parent
    while current:
        if current.type == "impl_item":
            # Check if this impl has a trait (impl Trait for Type)
            # Trait impl has "for" keyword
            has_for = False
            for child in current.children:
                if child.type == "for":
                    has_for = True
                    break
            return has_for
        if current.type in ("source_file", "mod_item"):
            return False
        current = current.parent
    return False


def _is_in_trait_definition(node: Node) -> bool:
    """Check if node is inside trait definition (not impl)."""
    current = node.parent
    while current:
        if current.type == "trait_item":
            return True
        if current.type in ("source_file", "mod_item", "impl_item"):
            return False
        current = current.parent
    return False


def _get_parent_trait(node: Node) -> Optional[Node]:
    """Get parent trait_item node."""
    current = node.parent
    while current:
        if current.type == "trait_item":
            return current
        if current.type in ("source_file", "mod_item", "impl_item"):
            return None
        current = current.parent
    return None


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Rust element from node.

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        Element name or None if not found
    """
    # Search for child node with name
    for child in node.children:
        if child.type in ("identifier", "type_identifier"):
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _is_public_rust(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Rust element is public based on visibility modifier.

    Rules:
    - pub = public
    - pub(crate) = public (part of crate's public API)
    - pub(super) = public (part of module tree's public API)
    - pub(self) = private (effectively internal)
    - no modifier = private

    Special cases:
    - Methods in trait implementations are always public (they implement the trait contract)
    - Methods in trait definitions inherit visibility from the trait

    Args:
        node: Tree-sitter node of element
        doc: Tree-sitter document

    Returns:
        True if element is public, False if private
    """
    # Special case: methods in trait implementations are always public
    if node.type == "function_item" and _is_in_trait_impl(node):
        return True

    # Special case: methods in trait definitions inherit visibility from trait
    if node.type == "function_item" and _is_in_trait_definition(node):
        parent_trait = _get_parent_trait(node)
        if parent_trait:
            # Recursively check trait visibility
            return _is_public_rust(parent_trait, doc)

    # Search for visibility_modifier
    for child in node.children:
        if child.type == "visibility_modifier":
            modifier_text = doc.get_node_text(child)

            # pub(self) is effectively private
            if "pub(self)" in modifier_text:
                return False
            # pub, pub(crate), pub(super) are all public API
            elif modifier_text.strip().startswith("pub"):
                return True

    # No visibility modifier - private
    return False


def _impl_has_no_public_methods(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if impl block has no public methods.

    Empty impl blocks (no public methods) should be removed entirely.
    This is used as additional_check for impl_item profile.
    Returns True if impl SHOULD BE REMOVED (no public methods).

    Args:
        node: impl_item node
        doc: Tree-sitter document

    Returns:
        True if impl block has no public methods and should be removed
    """
    # Find the declaration_list (body) of the impl
    body_node = None
    for child in node.children:
        if child.type == "declaration_list":
            body_node = child
            break

    if not body_node:
        # No body - remove it
        return True

    # Check each function in the impl block
    for child in body_node.children:
        if child.type == "function_item":
            # Check visibility of this method
            if _is_public_rust(child, doc):
                return False  # Has public method, keep impl

    # No public methods found - remove impl
    return True


def _is_top_level_private_macro(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if macro invocation is top-level and private.

    Top-level means not inside any function/method body.
    Private means doesn't contain 'pub' keyword.

    Args:
        node: macro_invocation node
        doc: Tree-sitter document

    Returns:
        True if macro is top-level and private (should be removed)
    """
    # Check if inside function body
    current = node.parent
    while current:
        if current.type in ("block", "statement_block"):
            # Inside function body - don't remove
            return False
        if current.type in ("source_file", "mod_item"):
            # Top-level
            break
        current = current.parent

    # Top-level macro - check if it contains 'pub'
    macro_text = doc.get_node_text(node)
    return "pub" not in macro_text


def _compute_element_range(node: Node, element_type: str, doc: TreeSitterDocument) -> Optional[tuple[int, int]]:
    """Compute adjusted element range to include trailing comma."""
    return compute_element_range_with_trailing(
        node, element_type, doc,
        element_types={"field"},
        trailing_chars={","},
    )


# --- Rust Code Descriptor ---

RUST_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="rust",

    profiles=[
        # === Structs ===
        ElementProfile(
            name="struct",
            query="(struct_item) @element",
            is_public=_is_public_rust,
        ),

        # === Traits ===
        ElementProfile(
            name="trait",
            query="(trait_item) @element",
            is_public=_is_public_rust,
        ),

        # === Unions ===
        ElementProfile(
            name="union",
            query="(union_item) @element",
            is_public=_is_public_rust,
        ),

        # === Enums ===
        ElementProfile(
            name="enum",
            query="(enum_item) @element",
            is_public=_is_public_rust,
        ),

        # === Modules ===
        ElementProfile(
            name="mod",
            query="(mod_item) @element",
            is_public=_is_public_rust,
        ),

        # === Type Aliases ===
        ElementProfile(
            name="type",
            query="(type_item) @element",
            is_public=_is_public_rust,
        ),

        # === Functions ===
        # Top-level functions (not in impl)
        ElementProfile(
            name="function",
            query="(function_item) @element",
            is_public=_is_public_rust,
            additional_check=lambda node, doc: not is_inside_container(
                node,
                {"impl_item", "declaration_list"},
                boundary_types={"source_file", "mod_item"}
            ),
            has_body=True,
        ),

        # === Methods ===
        # Functions inside impl blocks
        ElementProfile(
            name="method",
            query="(function_item) @element",
            is_public=_is_public_rust,
            additional_check=lambda node, doc: is_inside_container(
                node,
                {"impl_item", "declaration_list"},
                boundary_types={"source_file", "mod_item"}
            ),
            has_body=True,
        ),

        # === Struct Fields ===
        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            is_public=_is_public_rust,
        ),

        # === Constants ===
        ElementProfile(
            name="const",
            query="(const_item) @element",
            is_public=_is_public_rust,
        ),

        # === Statics ===
        ElementProfile(
            name="static",
            query="(static_item) @element",
            is_public=_is_public_rust,
        ),

        # === Impl Blocks ===
        # Remove impl blocks that have no public methods
        # (impl blocks for private types or with only private methods)
        ElementProfile(
            name="impl",
            query="(impl_item) @element",
            is_public=lambda node, doc: False,  # Always private (filtered by additional_check)
            additional_check=_impl_has_no_public_methods,
        ),

        # === Macro Invocations ===
        # Remove top-level macros that don't contain 'pub' (likely private)
        # Macros inside function bodies are kept (they're implementation details)
        ElementProfile(
            name="macro",
            query="(macro_invocation) @element",
            is_public=lambda node, doc: False,  # Always private (filtered by additional_check)
            additional_check=_is_top_level_private_macro,
        ),
    ],

    decorator_types={"attribute_item", "inner_attribute_item"},
    comment_types={"line_comment", "block_comment"},
    name_extractor=_extract_name,
    compute_element_range=_compute_element_range,
)


__all__ = ["RUST_CODE_DESCRIPTOR"]
