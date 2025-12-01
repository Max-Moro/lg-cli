"""
Go-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Go.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class GoCodeAnalyzer(CodeAnalyzer):
    """Go-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Go element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "struct", "interface", "type", "const", "var", "field"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "function_declaration":
            return "function"
        elif node_type == "method_declaration":
            return "method"
        elif node_type == "type_declaration":
            # Determine if it's struct, interface, or type alias
            return self._determine_type_declaration_kind(node)
        elif node_type == "const_declaration":
            return "const"
        elif node_type == "var_declaration":
            return "var"
        elif node_type == "short_var_declaration":
            return "var"
        elif node_type == "field_declaration":
            return "field"
        else:
            return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of Go element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # For type declarations, look inside type_spec or type_alias
        if node.type == "type_declaration":
            for child in node.children:
                if child.type in ("type_spec", "type_alias"):
                    for grandchild in child.children:
                        if grandchild.type == "type_identifier":
                            return self.doc.get_node_text(grandchild)

        # For method declarations, get field_identifier (method name)
        if node.type == "method_declaration":
            for child in node.children:
                if child.type == "field_identifier":
                    return self.doc.get_node_text(child)

        # For var/const declarations
        if node.type in ("var_declaration", "const_declaration"):
            for child in node.children:
                if child.type in ("var_spec", "const_spec"):
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)

        # For short variable declarations
        if node.type == "short_var_declaration":
            for child in node.children:
                if child.type == "expression_list":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)

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
        Determine visibility of Go element by naming convention.

        Go rules:
        - Names starting with uppercase letter are exported (public)
        - Names starting with lowercase letter are unexported (private)

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        element_name = self.extract_element_name(node)
        if not element_name:
            return Visibility.PUBLIC

        # Go convention: uppercase first letter = exported (public)
        if element_name and element_name[0].isupper():
            return Visibility.PUBLIC
        else:
            return Visibility.PRIVATE

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of Go element.

        Go rules:
        - Methods are never directly exported (they belong to types)
        - Top-level functions, types, variables, constants are exported if public
        - Package-level elements with lowercase names are not exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Methods are never directly exported
        if node.type == "method_declaration":
            return ExportStatus.NOT_EXPORTED

        # For top-level elements, check naming convention
        visibility = self.determine_visibility(node)

        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method (has receiver).

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is a method declaration
        """
        # In Go, methods are explicitly marked as method_declaration
        return node.type == "method_declaration"

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find function or method declaration for given node by walking up the tree.

        Args:
            node: Node to find parent function

        Returns:
            Function/method definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in ("function_declaration", "method_declaration", "func_literal"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in Go.

        Go doesn't have decorators.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in Go.

        Go doesn't have decorators.

        Returns:
            Empty set
        """
        return set()

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Go-specific private elements.

        Includes unexported types, variables, constants, and private struct fields.

        Returns:
            List of Go-specific private elements
        """
        private_elements = []

        # Go-specific elements
        self._collect_type_aliases(private_elements)
        self._collect_variables(private_elements)
        self._collect_struct_fields(private_elements)

        return private_elements

    def _collect_type_aliases(self, private_elements: List[ElementInfo]) -> None:
        """Collect unexported type declarations."""
        type_aliases = self.doc.query_opt("type_aliases")
        for node, capture_name in type_aliases:
            if capture_name == "type_name":
                # Navigate to type_spec/type_alias -> type_declaration
                parent = node.parent
                if parent and parent.parent:
                    type_decl = parent.parent
                    element_info = self.analyze_element(type_decl)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_variables(self, private_elements: List[ElementInfo]) -> None:
        """Collect unexported module-level variables and constants."""
        # Collect var declarations
        variables = self.doc.query_opt("variables")
        for node, capture_name in variables:
            if capture_name in ("var_name", "const_name"):
                # Navigate to parent declaration
                var_spec = node.parent
                if var_spec and var_spec.parent:
                    var_decl = var_spec.parent

                    # Skip variable declarations inside function bodies
                    # Only collect module-level variables
                    if self._is_inside_function_body(var_decl):
                        continue

                    element_info = self.analyze_element(var_decl)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_struct_fields(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect unexported (private) fields from exported (public) structs.

        In Go, even exported structs can have unexported fields (lowercase names).
        These fields should be removed in public API mode.
        """
        struct_fields = self.doc.query_opt("struct_fields")
        for node, capture_name in struct_fields:
            if capture_name == "field_name":
                field_decl = node.parent
                if field_decl and field_decl.type == "field_declaration":
                    # Analyze the field
                    element_info = self.analyze_element(field_decl)

                    # Only collect if field is private (lowercase name)
                    # AND it's in a public (exported) struct
                    if not element_info.is_public and self._is_in_exported_struct(field_decl):
                        private_elements.append(element_info)

    def _is_in_exported_struct(self, node: Node) -> bool:
        """
        Check if node is inside an exported struct type.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if inside exported struct
        """
        current = node.parent
        while current:
            if current.type == "type_spec":
                # Find the struct name
                for child in current.children:
                    if child.type == "type_identifier":
                        name = self.doc.get_node_text(child)
                        # Exported if starts with uppercase
                        return name[0].isupper() if name else False
            if current.type == "source_file":
                break
            current = current.parent
        return False

    def _is_inside_function_body(self, node: Node) -> bool:
        """
        Check if node is inside a function body.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside a function body
        """
        current = node.parent
        while current:
            if current.type == "block":
                # Check if this block is a function body
                if current.parent and current.parent.type == "function_declaration":
                    return True
                if current.parent and current.parent.type == "method_declaration":
                    return True
            # Stop at source_file (module level)
            if current.type == "source_file":
                return False
            current = current.parent
        return False

    def _determine_type_declaration_kind(self, node: Node) -> str:
        """
        Determine the kind of type declaration (struct, interface, alias).

        Args:
            node: type_declaration node

        Returns:
            String: "struct", "interface", or "type"
        """
        for child in node.children:
            if child.type == "type_spec":
                for grandchild in child.children:
                    if grandchild.type == "struct_type":
                        return "struct"
                    elif grandchild.type == "interface_type":
                        return "interface"
        return "type"

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Go.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
