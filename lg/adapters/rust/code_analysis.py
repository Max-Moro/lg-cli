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

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Rust-specific private elements.

        Includes structs, enums, traits, modules, type aliases, variables, struct fields, macro invocations,
        and impl blocks that contain only private methods.

        Returns:
            List of Rust-specific private elements
        """
        private_elements = []

        # Rust-specific elements
        self._collect_structs(private_elements)
        self._collect_enums(private_elements)
        self._collect_traits(private_elements)
        self._collect_modules(private_elements)
        self._collect_type_aliases(private_elements)
        self._collect_variables(private_elements)
        self._collect_struct_fields(private_elements)
        self._collect_empty_impl_blocks(private_elements)
        self._collect_macro_invocations(private_elements)

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

    def _collect_macro_invocations(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect macro invocations that contain only private items.

        This handles macros like lazy_static! where static items are defined
        inside the macro invocation's token tree.
        """
        macros = self.doc.query_opt("macros")
        for node, capture_name in macros:
            if capture_name == "macro_call":
                # Get the full text of the macro invocation
                macro_text = self.doc.get_node_text(node)

                # Check if this looks like a lazy_static! or similar macro with static items
                # If it contains "static ref" but NOT "pub static ref", it's private
                if "static ref" in macro_text or "static mut" in macro_text:
                    # Check if any of the static declarations are public
                    has_public = "pub static" in macro_text

                    if not has_public:
                        # All static items in this macro are private, so remove the macro
                        # Note: Simply add the element - it contains only private items
                        private_elements.append(self.analyze_element(node))

    def _collect_structs(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public structs and their associated impl blocks."""
        classes = self.doc.query_opt("classes")
        for node, capture_name in classes:
            if capture_name == "struct_name":
                struct_def = node.parent
                if struct_def:
                    element_info = self.analyze_element(struct_def)
                    if not element_info.in_public_api:
                        # Add the private struct
                        private_elements.append(element_info)

                        # Also find and add all impl blocks for this struct
                        if element_info.name:
                            impl_blocks = self._find_impl_blocks_for_type(element_info.name)
                            for impl_block in impl_blocks:
                                impl_element_info = self.analyze_element(impl_block)
                                private_elements.append(impl_element_info)

    def _collect_enums(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public enums and their associated impl blocks."""
        classes = self.doc.query_opt("classes")
        for node, capture_name in classes:
            if capture_name == "enum_name":
                enum_def = node.parent
                if enum_def:
                    element_info = self.analyze_element(enum_def)
                    if not element_info.in_public_api:
                        # Add the private enum
                        private_elements.append(element_info)

                        # Also find and add all impl blocks for this enum
                        if element_info.name:
                            impl_blocks = self._find_impl_blocks_for_type(element_info.name)
                            for impl_block in impl_blocks:
                                impl_element_info = self.analyze_element(impl_block)
                                private_elements.append(impl_element_info)

    def _collect_struct_fields(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect non-pub (private) fields from pub structs.

        In Rust, even pub structs can have private fields (without pub modifier).
        These fields should be removed in public API mode.
        """
        struct_fields = self.doc.query_opt("struct_fields")
        for node, capture_name in struct_fields:
            if capture_name == "field_name":
                field_decl = node.parent
                if field_decl and field_decl.type == "field_declaration":
                    # Analyze the field
                    element_info = self.analyze_element(field_decl)

                    # Only collect if field is private (no pub modifier)
                    # AND it's in a pub struct
                    if not element_info.is_public and self._is_in_pub_struct(field_decl):
                        private_elements.append(element_info)

    def _is_in_pub_struct(self, node: Node) -> bool:
        """
        Check if node is inside a pub struct.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if inside pub struct
        """
        current = node.parent
        while current:
            if current.type == "struct_item":
                # Check if this struct has pub visibility
                for child in current.children:
                    if child.type == "visibility_modifier":
                        modifier_text = self.doc.get_node_text(child)
                        # pub, pub(crate), pub(super) - all count as public structs
                        return "pub" in modifier_text
                # No pub modifier found on struct
                return False
            if current.type == "source_file":
                break
            current = current.parent
        return False

    def _find_impl_blocks_for_type(self, type_name: str) -> List[Node]:
        """
        Find all impl blocks for a given type name.

        Args:
            type_name: Name of the type to find impl blocks for

        Returns:
            List of impl_item nodes for this type
        """
        impl_blocks = []
        impls = self.doc.query_opt("impls")

        for node, capture_name in impls:
            if capture_name == "impl_type":
                # Check if this impl is for our type
                impl_type_text = self.doc.get_node_text(node)
                if impl_type_text == type_name:
                    # Navigate to parent impl_item
                    impl_item = node.parent
                    while impl_item and impl_item.type != "impl_item":
                        impl_item = impl_item.parent
                    if impl_item and impl_item.type == "impl_item":
                        impl_blocks.append(impl_item)

        return impl_blocks

    def _collect_empty_impl_blocks(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect impl blocks that contain only private/non-pub methods.

        Such impl blocks are pointless in public API and should be completely removed.
        """
        impls = self.doc.query_opt("impls")
        for node, capture_name in impls:
            if capture_name in ("impl_block", "trait_impl"):
                # Check if this impl block has any public methods
                has_public_methods = self._impl_has_public_methods(node)

                if not has_public_methods:
                    # No public methods - mark entire impl block for removal
                    element_info = self.analyze_element(node)
                    private_elements.append(element_info)

    def _impl_has_public_methods(self, impl_node: Node) -> bool:
        """
        Check if an impl block contains any public methods.

        Args:
            impl_node: impl_item node

        Returns:
            True if impl block has at least one public method
        """
        # Find the declaration_list (body) of the impl
        body_node = None
        for child in impl_node.children:
            if child.type == "declaration_list":
                body_node = child
                break

        if not body_node:
            return False

        # Check each function in the impl block
        for child in body_node.children:
            if child.type == "function_item":
                element_info = self.analyze_element(child)
                if element_info.is_public:
                    return True

        return False

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Rust.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "block_comment", "newline", "\n", " ", "\t")
