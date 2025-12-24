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
    """
    for child in node.children:
        if child.type in ("identifier", "type_identifier"):
            return doc.get_node_text(child)

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
    """
    # Special case: methods in trait implementations are always public
    if node.type == "function_item" and _is_in_trait_impl(node):
        return True

    # Special case: methods in trait definitions inherit visibility from trait
    if node.type == "function_item" and _is_in_trait_definition(node):
        parent_trait = _get_parent_trait(node)
        if parent_trait:
            return _is_public_rust(parent_trait, doc)

    for child in node.children:
        if child.type == "visibility_modifier":
            modifier_text = doc.get_node_text(child)

            # pub(self) is effectively private
            if "pub(self)" in modifier_text:
                return False
            # pub, pub(crate), pub(super) are all public API
            elif modifier_text.strip().startswith("pub"):
                return True

    return False


def _impl_has_no_public_methods(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if impl block has no public methods.

    Empty impl blocks (no public methods) should be removed entirely.
    This is used as additional_check for impl_item profile.
    Returns True if impl SHOULD BE REMOVED (no public methods).
    """
    body_node = None
    for child in node.children:
        if child.type == "declaration_list":
            body_node = child
            break

    if not body_node:
        return True

    for child in body_node.children:
        if child.type == "function_item":
            if _is_public_rust(child, doc):
                return False

    return True


def _is_top_level_private_macro(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if macro invocation is top-level and private.

    Top-level means not inside any function/method body.
    Private means doesn't contain 'pub' keyword.
    """
    current = node.parent
    while current:
        if current.type in ("block", "statement_block"):
            return False
        if current.type in ("source_file", "mod_item"):
            break
        current = current.parent

    macro_text = doc.get_node_text(node)
    return "pub" not in macro_text


def _compute_element_range(node: Node, element_type: str, doc: TreeSitterDocument) -> Optional[tuple[int, int]]:
    """Compute adjusted element range to include trailing comma."""
    return compute_element_range_with_trailing(
        node, element_type, doc,
        element_types={"field"},
        trailing_chars={","},
    )


RUST_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="rust",

    profiles=[
        ElementProfile(
            name="struct",
            query="(struct_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="trait",
            query="(trait_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="union",
            query="(union_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="enum",
            query="(enum_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="mod",
            query="(mod_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="type",
            query="(type_item) @element",
            is_public=_is_public_rust,
        ),

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

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="const",
            query="(const_item) @element",
            is_public=_is_public_rust,
        ),

        ElementProfile(
            name="static",
            query="(static_item) @element",
            is_public=_is_public_rust,
        ),

        # Remove impl blocks that have no public methods
        ElementProfile(
            name="impl",
            query="(impl_item) @element",
            is_public=lambda node, doc: False,
            additional_check=_impl_has_no_public_methods,
        ),

        # Remove top-level macros that don't contain 'pub'
        ElementProfile(
            name="macro",
            query="(macro_invocation) @element",
            is_public=lambda node, doc: False,
            additional_check=_is_top_level_private_macro,
        ),
    ],

    decorator_types={"attribute_item", "inner_attribute_item"},
    comment_types={"line_comment", "block_comment"},
    name_extractor=_extract_name,
    compute_element_range=_compute_element_range,
)


__all__ = ["RUST_CODE_DESCRIPTOR"]
