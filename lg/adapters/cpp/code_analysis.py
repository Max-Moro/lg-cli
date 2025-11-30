"""
C++-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for C++.
"""

from __future__ import annotations

from typing import List, Optional, Set, Dict

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo, FunctionGroup
from ..tree_sitter_support import Node


class CppCodeAnalyzer(CodeAnalyzer):
    """C++-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of C++ element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "struct", "namespace", "template", "enum"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "class_specifier":
            return "class"
        elif node_type == "struct_specifier":
            return "struct"
        elif node_type == "union_specifier":
            return "union"
        elif node_type == "enum_specifier":
            return "enum"
        elif node_type == "namespace_definition":
            return "namespace"
        elif node_type == "template_declaration":
            return "template"
        elif node_type == "function_definition":
            return "method" if self.is_method_context(node) else "function"
        else:
            # Fallback: determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of C++ element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # For qualified identifiers (e.g., namespace::class::method)
        if node.type == "qualified_identifier":
            # Get the last identifier in the chain
            for child in reversed(node.children):
                if child.type == "identifier":
                    return self.doc.get_node_text(child)

        # Search for child node with name
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "field_identifier"):
                return self.doc.get_node_text(child)

        # For some node types, name may be in the name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine visibility of C++ element.

        C++ rules:
        - Elements in private: section - private
        - Elements in protected: section - protected
        - Elements in public: section or no section - public
        - For class/struct, need to find which access specifier section it's in

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # For class members, find the access specifier
        visibility = self._find_access_specifier(node)
        if visibility is not None:
            return visibility

        # Default: public for functions, structs; depends on context for class members
        if self.is_method_context(node):
            # In a class/struct, default is private for class, public for struct
            parent_class = self._find_parent_class_or_struct(node)
            if parent_class and parent_class.type == "class_specifier":
                return Visibility.PRIVATE  # Default for class
            else:
                return Visibility.PUBLIC  # Default for struct
        else:
            return Visibility.PUBLIC  # Top-level functions are public

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of C++ element.

        C++ doesn't have explicit export mechanism like ES6 modules.
        We consider:
        - Functions/classes in headers as potentially exported (public API)
        - Static functions as not exported
        - Anonymous namespaces as not exported
        - Everything else as exported by default

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Check for static storage class specifier
        if self._has_static_specifier(node):
            return ExportStatus.NOT_EXPORTED

        # Check if in anonymous namespace
        if self._in_anonymous_namespace(node):
            return ExportStatus.NOT_EXPORTED

        # Methods are never directly exported
        if node.type in ("function_definition",) and self.is_method_context(node):
            return ExportStatus.NOT_EXPORTED

        # For top-level elements, consider them exported
        return ExportStatus.EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method of C++ class/struct.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is class method, False if top-level function
        """
        # Walk up the tree looking for class/struct definition
        current = node.parent
        while current:
            if current.type in ("class_specifier", "struct_specifier", "union_specifier", "field_declaration_list"):
                return True
            # Stop at namespace or file boundaries
            if current.type in ("namespace_definition", "translation_unit"):
                break
            current = current.parent
        return False

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find function_definition for given node by walking up the tree.

        Args:
            node: Node to find parent function

        Returns:
            Function definition or None if not found
        """
        current = node.parent
        while current:
            if current.type == "function_definition":
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in C++.

        C++ doesn't have decorators.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in C++.

        C++ has attributes ([[attribute]]) but they're not decorators.

        Returns:
            Empty set
        """
        return set()

    def collect_function_like_elements(self) -> Dict[Node, FunctionGroup]:
        """
        Collect functions and class methods for C++.

        Overrides base method to also include class methods from separate query.

        Returns:
            Dictionary: function_node -> FunctionGroup
        """
        # Collect free functions using base implementation
        function_groups = super().collect_function_like_elements()

        # Also collect class methods from separate query
        if self.doc.has_query("class_methods"):
            class_methods = self.doc.query("class_methods")
            method_groups = self._group_function_captures(class_methods)
            function_groups.update(method_groups)

        return function_groups

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect C++-specific private elements.

        Includes namespaces, templates, enums, and class members.

        Returns:
            List of C++-specific private elements
        """
        private_elements = []

        # C++-specific elements
        self._collect_namespaces(private_elements)
        self._collect_enums(private_elements)

        return private_elements

    def _collect_namespaces(self, private_elements: List[ElementInfo]) -> None:
        """Collect anonymous or internal namespaces."""
        namespaces = self.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                if namespace_def:
                    element_info = self.analyze_element(namespace_def)
                    # Anonymous namespaces don't have names
                    if element_info.name is None or element_info.name == "":
                        private_elements.append(element_info)

    def _collect_enums(self, private_elements: List[ElementInfo]) -> None:
        """Collect private enums."""
        enums = self.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                if enum_def:
                    element_info = self.analyze_element(enum_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _find_access_specifier(self, node: Node) -> Optional[Visibility]:
        """
        Find the access specifier for a class member by looking at preceding siblings.

        Args:
            node: Node to find access specifier for

        Returns:
            Visibility or None if not found
        """
        if not node.parent:
            return None

        # Look backwards through siblings to find access specifier
        siblings = node.parent.children
        current_access = None

        for sibling in siblings:
            if sibling == node:
                return current_access

            if sibling.type == "access_specifier":
                specifier_text = self.doc.get_node_text(sibling)
                if "public" in specifier_text:
                    current_access = Visibility.PUBLIC
                elif "protected" in specifier_text:
                    current_access = Visibility.PROTECTED
                elif "private" in specifier_text:
                    current_access = Visibility.PRIVATE

        return current_access

    def _find_parent_class_or_struct(self, node: Node) -> Optional[Node]:
        """Find parent class or struct specifier."""
        current = node.parent
        while current:
            if current.type in ("class_specifier", "struct_specifier"):
                return current
            current = current.parent
        return None

    def _has_static_specifier(self, node: Node) -> bool:
        """Check if node has static storage class specifier."""
        for child in node.children:
            if child.type == "storage_class_specifier":
                if "static" in self.doc.get_node_text(child):
                    return True
        return False

    def _in_anonymous_namespace(self, node: Node) -> bool:
        """Check if node is inside an anonymous namespace."""
        current = node.parent
        while current:
            if current.type == "namespace_definition":
                # Check if namespace has a name
                has_name = False
                for child in current.children:
                    if child.type == "namespace_identifier":
                        has_name = True
                        break
                if not has_name:
                    return True  # Anonymous namespace
            current = current.parent
        return False

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in C++.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
