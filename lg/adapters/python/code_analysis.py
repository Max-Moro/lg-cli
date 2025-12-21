"""
Python-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Python.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class PythonCodeAnalyzer(CodeAnalyzer):
    """Python-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Python element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class"
        """
        node_type = node.type
        
        if node_type == "class_definition":
            return "class"
        elif node_type == "function_definition":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "assignment":
            return "variable"
        else:
            # Fallback: try to determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of Python element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # Special handling for assignments
        if node.type == "assignment":
            # In assignment, the left side is the variable name
            for child in node.children:
                if child.type == "identifier":
                    return self.doc.get_node_text(child)

        # Search for child node with function/class/method name
        for child in node.children:
            if child.type == "identifier":
                return self.doc.get_node_text(child)

        # For some node types, name may be in the name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine visibility of Python element by underscore naming conventions.

        Rules:
        - Names starting with single _ are considered "protected" (internal)
        - Names starting with __ are considered "private"
        - Names without _ or with trailing _ are considered public
        - Special methods __method__ are considered public

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        element_name = self.extract_element_name(node)
        if not element_name:
            return Visibility.PUBLIC  # If name not found, consider public

        # Special Python methods (dunder methods) are considered public
        if element_name.startswith("__") and element_name.endswith("__"):
            return Visibility.PUBLIC

        # Names starting with two underscores are private
        if element_name.startswith("__"):
            return Visibility.PRIVATE

        # Names starting with one underscore are protected
        if element_name.startswith("_"):
            return Visibility.PROTECTED

        # All others are public
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of Python element.

        In Python, export is determined through __all__ or by default all public elements.
        Currently simplified implementation - all public elements are considered exported.

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # TODO: Implement __all__ check in future iterations
        visibility = self.determine_visibility(node)

        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method of Python class.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is class method, False if top-level function
        """
        # Walk up the tree looking for class definition
        current = node.parent
        while current:
            if current.type == "class_definition":
                return True
            # Stop at module/file boundaries
            if current.type in ("module", "program"):
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
        Return node types for wrapped decorated definitions in Python.

        Returns:
            Set of node types
        """
        return {
            "decorated_definition",    # Python @decorator
        }

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in Python.

        Returns:
            Set of node types
        """
        return {
            "decorator",              # Python @decorator
        }

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Python-specific private elements.

        Includes handling of variables/assignments and other Python-specific constructs.

        Returns:
            List of Python-specific private elements
        """
        private_elements = []

        # Collect assignments (variables)
        self._collect_variable_assignments(private_elements)

        return private_elements
    
    def _collect_variable_assignments(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect Python variables that should be removed in public API mode.

        Args:
            private_elements: List to add private elements to
        """
        assignments = self.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                # Get assignment statement node
                assignment_def = node.parent
                if assignment_def:
                    element_info = self.analyze_element(assignment_def)

                    # For top-level variables check visibility and export
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def compute_strippable_range(self, func_def: Node, body_node: Node) -> Tuple[int, int]:
        """
        Compute strippable range for Python function body.

        Handles:
        - Leading comments between ':' and body (include in stripping)
        - Docstrings at start of body (exclude from stripping)

        Args:
            func_def: Function definition node
            body_node: Function body node (block)

        Returns:
            Tuple of (start_byte, end_byte) for stripping
        """
        # Find start position: include leading comments
        start_byte = self._find_strippable_start(func_def, body_node)

        # Find end position: exclude docstring if present
        docstring = self._find_docstring(body_node)
        if docstring is not None:
            # Start after docstring, at first content on next line
            start_byte = self._find_next_content_byte(docstring.end_byte)

        return (start_byte, body_node.end_byte)

    def _find_strippable_start(self, func_def: Node, body_node: Node) -> int:
        """
        Find where stripping should start, including leading comments.

        In Python, comments between ':' and block are siblings of block,
        not children. We need to include them in the strippable range.

        Returns the start of the line containing the first strippable content,
        preserving indentation for proper placeholder formatting.
        """
        # Default: start from body
        earliest_start = body_node.start_byte

        # Look for comment siblings before body_node
        for child in func_def.children:
            if child.type == "comment":
                # Check if this comment is between ':' and block
                if child.start_byte < body_node.start_byte:
                    earliest_start = min(earliest_start, child.start_byte)
            elif child == body_node:
                break

        # Find start of line containing earliest_start
        # This preserves indentation in strippable_range
        text = self.doc.text
        line_start = text.rfind('\n', 0, earliest_start)
        if line_start == -1:
            return 0
        return line_start + 1

    def _find_docstring(self, body_node: Node) -> Optional[Node]:
        """Find docstring at the start of function body."""
        for child in body_node.children:
            if child.type == "expression_statement":
                for expr_child in child.children:
                    if expr_child.type == "string":
                        return child  # Return expression_statement
                # First expression_statement without string is not a docstring
                break
        return None

    def _find_next_content_byte(self, pos: int) -> int:
        """
        Find the start of the next line after position that contains content.

        Returns the position right after the newline (start of line with content),
        preserving indentation in the strippable_range for proper placeholder formatting.
        """
        text = self.doc.text
        newline_pos = text.find('\n', pos)
        if newline_pos == -1:
            return pos

        # Return position after newline (start of next line)
        # This preserves indentation in strippable_range
        return newline_pos + 1

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Python.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
