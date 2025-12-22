"""
Rust-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Rust.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node

if TYPE_CHECKING:
    from ..optimizations.public_api.profiles import LanguageElementProfiles


class RustCodeAnalyzer(CodeAnalyzer):
    """Rust-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Rust element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "struct", "enum", "trait", "impl", "mod", "const", "static", "field"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "function_item":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "struct_item":
            return "struct"
        elif node_type == "enum_item":
            return "enum"
        elif node_type == "trait_item":
            return "trait"
        elif node_type == "impl_item":
            return "impl"
        elif node_type == "mod_item":
            return "mod"
        elif node_type == "const_item":
            return "const"
        elif node_type == "static_item":
            return "static"
        elif node_type == "type_item":
            return "type"
        elif node_type == "union_item":
            return "union"
        elif node_type == "field_declaration":
            return "field"
        elif node_type == "macro_invocation":
            return "macro"
        else:
            # Fallback: determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of Rust element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # Search for child node with name
        for child in node.children:
            if child.type in ("identifier", "type_identifier"):
                return self.doc.get_node_text(child)

        # For some node types, name may be in the name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine visibility of Rust element by pub modifier.

        Rust rules:
        - pub - public
        - pub(crate) - crate-level (internal)
        - pub(super) - parent module (protected)
        - pub(self) - current module (effectively private)
        - No modifier - private (except for trait impl methods and trait methods)

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # Special case: methods in trait implementations are always public
        # (they implement the trait contract)
        if node.type == "function_item" and self._is_in_trait_impl(node):
            return Visibility.PUBLIC

        # Special case: methods in trait definitions inherit visibility from the trait
        if node.type in ("function_item", "function_signature_item") and self._is_in_trait(node):
            trait_node = self._find_parent_trait(node)
            if trait_node:
                return self.determine_visibility(trait_node)

        # Search for visibility_modifier
        for child in node.children:
            if child.type == "visibility_modifier":
                modifier_text = self.doc.get_node_text(child)

                # Check for qualified pub
                if "pub(crate)" in modifier_text:
                    return Visibility.INTERNAL
                elif "pub(super)" in modifier_text:
                    return Visibility.PROTECTED
                elif "pub(self)" in modifier_text:
                    return Visibility.PRIVATE
                elif modifier_text.strip() == "pub":
                    return Visibility.PUBLIC
                else:
                    # Other pub variants default to internal
                    return Visibility.INTERNAL

        # No visibility modifier - private
        return Visibility.PRIVATE

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of Rust element.

        Rust rules:
        - Methods inside impl blocks are NOT exported directly
        - Top-level pub items are exported (including pub(crate) and pub(super))
        - Private items are not exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Methods inside impl are never directly exported
        if self.is_method_context(node):
            return ExportStatus.NOT_EXPORTED

        # For top-level elements, check visibility
        visibility = self.determine_visibility(node)

        # pub, pub(crate), and pub(super) are all considered exported
        # Only truly private items are not exported
        if visibility in (Visibility.PUBLIC, Visibility.INTERNAL, Visibility.PROTECTED):
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is inside an impl block.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is inside an impl block
        """
        # Walk up the tree looking for impl_item
        current = node.parent
        while current:
            if current.type in ("impl_item", "declaration_list"):
                # Check if parent of declaration_list is impl_item
                if current.type == "declaration_list" and current.parent:
                    if current.parent.type == "impl_item":
                        return True
                elif current.type == "impl_item":
                    return True
            # Stop at module or crate boundaries
            if current.type in ("source_file", "mod_item"):
                break
            current = current.parent
        return False

    def _is_in_trait_impl(self, node: Node) -> bool:
        """
        Check if node is inside a trait implementation block.

        Trait impl: impl Trait for Type { ... }
        Regular impl: impl Type { ... }

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside a trait impl block
        """
        # Walk up to find impl_item
        current = node
        while current:
            if current.type == "impl_item":
                # Check if this impl has a 'for' keyword (trait impl)
                for child in current.children:
                    if child.type == "for":
                        return True
                return False
            current = current.parent
        return False

    def _is_in_trait(self, node: Node) -> bool:
        """
        Check if node is inside a trait definition.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside a trait definition
        """
        current = node.parent
        while current:
            if current.type == "trait_item":
                return True
            if current.type in ("source_file", "mod_item"):
                break
            current = current.parent
        return False

    def _find_parent_trait(self, node: Node) -> Optional[Node]:
        """
        Find parent trait_item node.

        Args:
            node: Tree-sitter node to find parent trait for

        Returns:
            Parent trait_item node or None if not found
        """
        current = node.parent
        while current:
            if current.type == "trait_item":
                return current
            if current.type in ("source_file", "mod_item"):
                break
            current = current.parent
        return None

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find function_item for given node by walking up the tree.

        Args:
            node: Node to find parent function

        Returns:
            Function definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in ("function_item", "closure_expression"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in Rust.

        Rust doesn't have decorator wrappers like Python.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual attributes in Rust.

        Returns:
            Set of node types
        """
        return {
            "attribute_item",
            "inner_attribute_item",
        }

    # Legacy collection methods removed - using profile-based collection

    def get_element_range_with_decorators(self, elem: ElementInfo) -> Tuple[int, int]:
        """
        Gets the range of element including its decorators/annotations.

        For Rust struct fields, also includes trailing comma for proper placeholder merging.

        Args:
            elem: Element

        Returns:
            Tuple (start_char, end_char) including all related decorators and trailing comma (for fields)
        """
        # Get base range from parent implementation
        start_char, end_char = super().get_element_range_with_decorators(elem)

        # For struct fields, extend range to include trailing comma
        if elem.element_type == "field":
            end_char = self._extend_to_trailing_comma(end_char)

        return start_char, end_char

    def _extend_to_trailing_comma(self, end_char: int) -> int:
        """
        Extend end position to include trailing comma if present.

        This is important for proper placeholder merging when removing multiple
        consecutive struct fields.

        Args:
            end_char: Current end character position

        Returns:
            Extended end position including trailing comma (if found)
        """
        text = self.doc.text
        # Look ahead for comma, skipping only whitespace (not newlines)
        pos = end_char
        while pos < len(text) and text[pos] in ' \t':
            pos += 1

        # If we found a comma, include it
        if pos < len(text) and text[pos] == ',':
            return pos + 1

        return end_char

    def get_element_profiles(self) -> Optional[LanguageElementProfiles]:
        """
        Return Rust element profiles for profile-based public API collection.

        Returns:
            LanguageElementProfiles for Rust
        """
        from ..optimizations.public_api.language_profiles.rust import RUST_PROFILES
        return RUST_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Rust.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "block_comment", "newline", "\n", " ", "\t")
