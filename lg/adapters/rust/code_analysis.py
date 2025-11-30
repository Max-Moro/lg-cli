"""
Rust-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Rust.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class RustCodeAnalyzer(CodeAnalyzer):
    """Rust-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Rust element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "struct", "enum", "trait", "impl", "mod", "const", "static"
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
        - pub(super) - parent module
        - pub(self) - current module (effectively private)
        - No modifier - private

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
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
        - Top-level pub items are exported
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

        # Only truly public items are exported
        if visibility == Visibility.PUBLIC:
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

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Rust-specific private elements.

        Includes traits, impl blocks, modules, and type aliases.

        Returns:
            List of Rust-specific private elements
        """
        private_elements = []

        # Rust-specific elements
        self._collect_traits(private_elements)
        self._collect_impl_blocks(private_elements)
        self._collect_modules(private_elements)
        self._collect_type_aliases(private_elements)
        self._collect_variables(private_elements)

        return private_elements

    def _collect_traits(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public traits."""
        traits = self.doc.query_opt("traits")
        for node, capture_name in traits:
            if capture_name == "trait_name":
                trait_def = node.parent
                if trait_def:
                    element_info = self.analyze_element(trait_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_impl_blocks(self, private_elements: List[ElementInfo]) -> None:
        """Collect private impl blocks."""
        impls = self.doc.query_opt("impls")
        for node, capture_name in impls:
            if capture_name in ("impl_type", "impl_trait"):
                # Navigate to impl_item
                if node.parent and node.parent.type == "impl_item":
                    impl_def = node.parent
                    element_info = self.analyze_element(impl_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_modules(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public modules."""
        modules = self.doc.query_opt("modules")
        for node, capture_name in modules:
            if capture_name == "module_name":
                mod_def = node.parent
                if mod_def:
                    element_info = self.analyze_element(mod_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_type_aliases(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public type aliases."""
        type_aliases = self.doc.query_opt("type_aliases")
        for node, capture_name in type_aliases:
            if capture_name == "type_alias_name":
                type_def = node.parent
                if type_def:
                    element_info = self.analyze_element(type_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_variables(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public constants and statics."""
        variables = self.doc.query_opt("variables")
        for node, capture_name in variables:
            if capture_name in ("const_name", "static_name"):
                var_def = node.parent
                if var_def:
                    element_info = self.analyze_element(var_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Rust.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "block_comment", "newline", "\n", " ", "\t")
