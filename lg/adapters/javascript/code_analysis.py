"""
JavaScript-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for JavaScript.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class JavaScriptCodeAnalyzer(CodeAnalyzer):
    """JavaScript-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of JavaScript element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "variable", "arrow_function"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "class_declaration":
            return "class"
        elif node_type in ("function_declaration", "function_expression", "generator_function", "generator_function_declaration"):
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "arrow_function":
            return "arrow_function"
        elif node_type == "method_definition":
            return "method"
        elif node_type == "variable_declaration":
            return "variable"
        else:
            # Fallback: try to determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of JavaScript element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # Special handling for variable_declaration
        if node.type == "variable_declaration":
            # Search for variable_declarator with name
            for child in node.children:
                if child.type == "variable_declarator":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)

        # Search for child node with name
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                return self.doc.get_node_text(child)

        # For some node types, name may be in the name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine visibility of JavaScript element by naming conventions.

        JavaScript rules (convention-based):
        - Names starting with _ are considered private (by convention)
        - Names starting with # are truly private (ES2022+)
        - All others are public

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        element_name = self.extract_element_name(node)
        if not element_name:
            return Visibility.PUBLIC

        # ES2022+ private fields/methods with #
        if element_name.startswith("#"):
            return Visibility.PRIVATE

        # Convention: _ prefix indicates private
        if element_name.startswith("_"):
            return Visibility.PRIVATE

        # All others are public
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of JavaScript element.

        Rules:
        - Methods inside classes are NOT exported directly
        - Top-level functions, classes, variables are exported if they have export keyword
        - Private elements are never exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Methods are never directly exported
        if node.type == "method_definition":
            return ExportStatus.NOT_EXPORTED

        # Check if this is a top-level element with export
        node_text = self.doc.get_node_text(node)

        # Simple check: element is exported if it starts with export
        if node_text.strip().startswith("export "):
            return ExportStatus.EXPORTED

        # Check parent for export statement
        current = node
        while current and current.type not in ("program", "source_file"):
            if current.type == "export_statement":
                return ExportStatus.EXPORTED
            current = current.parent

        # Additional check by searching for export at start of line
        if self._check_export_in_source_line(node):
            return ExportStatus.EXPORTED

        return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method of JavaScript class.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is class method, False if top-level function
        """
        # Walk up the tree looking for class definition
        current = node.parent
        while current:
            if current.type in ("class_declaration", "class_body", "class"):
                return True
            # Stop at module/file boundaries
            if current.type in ("program", "source_file"):
                break
            current = current.parent
        return False

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find function definition for given node by walking up the tree.

        Args:
            node: Node to find parent function

        Returns:
            Function definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in ("function_declaration", "method_definition", "arrow_function",
                               "function_expression", "generator_function", "generator_function_declaration"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in JavaScript.

        JavaScript doesn't have decorator wrappers (yet).

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in JavaScript.

        Returns:
            Empty set (decorators are a Stage 3 proposal, not widely used)
        """
        return set()

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect JavaScript-specific private elements.

        Includes class members, variables, and exports.

        Returns:
            List of JavaScript-specific private elements
        """
        private_elements = []

        # JavaScript-specific elements
        self._collect_variables(private_elements)
        self._collect_class_members(private_elements)

        return private_elements

    def _collect_variables(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported variables."""
        variables = self.doc.query_opt("variables")
        for node, capture_name in variables:
            if capture_name == "variable_name":
                parent = node.parent
                if parent and getattr(parent, "parent", None):
                    variable_def = parent.parent  # variable_declarator -> variable_declaration
                else:
                    variable_def = None
                if variable_def is not None:
                    element_info = self.analyze_element(variable_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_class_members(self, private_elements: List[ElementInfo]) -> None:
        """Collect private class members (by convention or ES2022+ private fields)."""
        # Note: Tree-sitter may not have specific queries for class members
        # This is a simplified implementation
        pass

    def _check_export_in_source_line(self, node: Node) -> bool:
        """
        Check for 'export' in element's source line.
        This is a fallback for cases where Tree-sitter doesn't parse export correctly.

        Args:
            node: Tree-sitter node of element

        Returns:
            True if export found at start of line
        """
        start_line, _ = self.doc.get_line_range(node)
        lines = self.doc.text.split('\n')

        if start_line < len(lines):
            line_text = lines[start_line].strip()
            if line_text.startswith('export '):
                return True

        return False

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in JavaScript.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
