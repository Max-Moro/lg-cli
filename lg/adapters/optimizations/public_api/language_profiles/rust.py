"""
Element profiles for Rust language.

Rust uses pub keyword for visibility with variants:
- pub - public
- pub(crate) - crate-level (internal)
- pub(super) - parent module (protected)
- pub(self) - current module (private)
- no modifier - private

Trait methods inherit visibility from the trait.
Methods in trait impls are always public.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....tree_sitter_support import Node, TreeSitterDocument

from ..profiles import ElementProfile, LanguageElementProfiles


# Helper functions

def is_in_trait_impl(node: Node) -> bool:
    """Check if node is inside trait implementation (impl Trait for Type)."""
    current = node.parent
    while current:
        if current.type == "impl_item":
            # Check if this impl has a trait (impl Trait for Type)
            # Trait impl has 'trait' field
            trait_node = None
            for child in current.children:
                if child.type in ("type_identifier", "scoped_type_identifier", "generic_type"):
                    # This might be the trait name
                    # In "impl Trait for Type", trait comes before "for"
                    trait_node = child
                    break

            # Check if there's a "for" keyword after the trait
            has_for = False
            for child in current.children:
                if child.type == "for":
                    has_for = True
                    break

            return has_for and trait_node is not None
        if current.type in ("source_file", "mod_item"):
            return False
        current = current.parent
    return False


def is_in_trait_definition(node: Node) -> bool:
    """Check if node is inside trait definition (not impl)."""
    current = node.parent
    while current:
        if current.type == "trait_item":
            return True
        if current.type in ("source_file", "mod_item", "impl_item"):
            return False
        current = current.parent
    return False


def get_parent_trait(node: Node) -> Node | None:
    """Get parent trait_item node."""
    current = node.parent
    while current:
        if current.type == "trait_item":
            return current
        if current.type in ("source_file", "mod_item", "impl_item"):
            return None
        current = current.parent
    return None


def rust_public_visibility(node: Node, doc: TreeSitterDocument) -> str:
    """
    Custom visibility check for Rust that treats pub, pub(crate), and pub(super) as public.

    Special cases:
    - Methods in trait implementations are always public (they implement the trait contract)
    - Methods in trait definitions inherit visibility from the trait

    In public API mode, we want to keep:
    - pub (public)
    - pub(crate) (crate-level - part of crate's public API)
    - pub(super) (parent module - part of module tree's public API)
    - trait impl methods (always public)
    - trait definition methods (inherit from trait visibility)

    We want to remove:
    - pub(self) (current module only)
    - no modifier (private)

    Returns:
        "public" if element should be in public API, "private" otherwise
    """
    # Special case: methods in trait implementations are always public
    if node.type == "function_item" and is_in_trait_impl(node):
        return "public"

    # Special case: methods in trait definitions inherit visibility from trait
    if node.type == "function_item" and is_in_trait_definition(node):
        parent_trait = get_parent_trait(node)
        if parent_trait:
            # Recursively check trait visibility
            return rust_public_visibility(parent_trait, doc)

    # Search for visibility_modifier
    for child in node.children:
        if child.type == "visibility_modifier":
            modifier_text = doc.get_node_text(child)

            # pub(self) is effectively private
            if "pub(self)" in modifier_text:
                return "private"
            # pub, pub(crate), pub(super) are all public API
            elif modifier_text.strip().startswith("pub"):
                return "public"

    # No visibility modifier - private
    return "private"


def is_inside_impl(node: Node) -> bool:
    """Check if node is inside impl block."""
    current = node.parent
    while current:
        if current.type in ("impl_item", "declaration_list"):
            if current.type == "declaration_list" and current.parent:
                if current.parent.type == "impl_item":
                    return True
            elif current.type == "impl_item":
                return True
        if current.type in ("source_file", "mod_item"):
            return False
        current = current.parent
    return False


def is_top_level_private_macro(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if macro invocation is top-level and private.

    Top-level means not inside any function/method body.
    Private means doesn't contain 'pub' keyword.
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


def impl_has_no_public_methods(impl_node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if impl block has no public methods.

    Empty impl blocks (no public methods) should be removed entirely.
    This is used as additional_check for impl_item profile.
    """
    # Find the declaration_list (body) of the impl
    body_node = None
    for child in impl_node.children:
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
            visibility = rust_public_visibility(child, doc)
            if visibility == "public":
                return False  # Has public method, keep impl

    # No public methods found - remove impl
    return True


# Rust element profiles

RUST_PROFILES = LanguageElementProfiles(
    language="rust",
    profiles=[
        # === Structs ===

        ElementProfile(
            name="struct",
            query="(struct_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Traits ===

        ElementProfile(
            name="trait",
            query="(trait_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Unions ===

        ElementProfile(
            name="union",
            query="(union_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Enums ===

        ElementProfile(
            name="enum",
            query="(enum_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Modules ===

        ElementProfile(
            name="mod",
            query="(mod_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Type Aliases ===

        ElementProfile(
            name="type",
            query="(type_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Functions ===
        # Top-level functions (not in impl)

        ElementProfile(
            name="function",
            query="(function_item) @element",
            additional_check=lambda node, doc: not is_inside_impl(node),
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Methods ===
        # Functions inside impl blocks

        ElementProfile(
            name="method",
            query="(function_item) @element",
            additional_check=lambda node, doc: is_inside_impl(node),
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Struct Fields ===

        ElementProfile(
            name="field",
            query="(field_declaration) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Constants ===

        ElementProfile(
            name="const",
            query="(const_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Statics ===

        ElementProfile(
            name="static",
            query="(static_item) @element",
            visibility_check=rust_public_visibility,
            uses_visibility_for_public_api=True
        ),

        # === Impl Blocks ===
        # Remove impl blocks that have no public methods
        # (impl blocks for private types or with only private methods)

        ElementProfile(
            name="impl",
            query="(impl_item) @element",
            additional_check=impl_has_no_public_methods,
            uses_visibility_for_public_api=False  # Use additional_check instead
        ),

        # === Macro Invocations ===
        # Remove top-level macros that don't contain 'pub' (likely private)
        # Macros inside function bodies are kept (they're implementation details)

        ElementProfile(
            name="macro",
            query="(macro_invocation) @element",
            additional_check=is_top_level_private_macro,
            uses_visibility_for_public_api=False
        ),
    ]
)
