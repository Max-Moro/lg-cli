"""
Scala-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Scala.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class ScalaCodeAnalyzer(CodeAnalyzer):
    """Scala-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Scala element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "object", "trait", "case_class", "val", "var"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "class_definition":
            # Check if it's a case class
            if self._is_case_class(node):
                return "case_class"
            return "class"
        elif node_type == "object_definition":
            return "object"
        elif node_type == "trait_definition":
            return "trait"
        elif node_type == "function_definition":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "function_declaration":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "val_definition":
            return "val"
        elif node_type == "var_definition":
            return "var"
        elif node_type == "type_definition":
            return "type"
        else:
            # Fallback: determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of Scala element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # Special handling for val/var definitions - name is in pattern field
        if node.type in ("val_definition", "var_definition", "val_declaration", "var_declaration"):
            pattern_node = node.child_by_field_name("pattern")
            if pattern_node and pattern_node.type == "identifier":
                return self.doc.get_node_text(pattern_node)

        # Search for child node with name
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
        Determine visibility of Scala element by access modifiers.

        Scala rules:
        - private - private
        - protected - protected
        - private[scope] or protected[scope] - qualified access
        - No modifier - public

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # Search for modifiers node
        for child in node.children:
            if child.type == "modifiers":
                modifier_text = self.doc.get_node_text(child)

                # Check for access modifiers
                if "private" in modifier_text:
                    return Visibility.PRIVATE
                elif "protected" in modifier_text:
                    return Visibility.PROTECTED

        # Default: public
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of Scala element.

        Scala rules:
        - Methods/fields inside classes/objects are NOT exported directly
        - Top-level public classes/objects/traits are exported
        - Private/protected elements are not exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Methods, vals, vars inside classes/objects are never directly exported
        if self.is_method_context(node):
            return ExportStatus.NOT_EXPORTED

        # For top-level elements, check visibility
        visibility = self.determine_visibility(node)

        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is inside a class, object, or trait.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is inside a class/object/trait
        """
        # Walk up the tree looking for class/object/trait definition
        current = node.parent
        while current:
            if current.type in ("class_definition", "object_definition", "trait_definition", "template_body"):
                return True
            # Stop at file boundaries or package
            if current.type in ("compilation_unit", "package_clause"):
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
            if current.type in ("function_definition", "function_declaration"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in Scala.

        Scala doesn't have decorator wrappers like Python.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual annotations in Scala.

        Returns:
            Set of node types
        """
        return {
            "annotation",
        }

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Scala-specific private elements.

        Includes objects, traits, case classes, classes, class members, type aliases, and variables.

        Returns:
            List of Scala-specific private elements
        """
        private_elements = []

        # Scala-specific elements
        self._collect_objects(private_elements)
        self._collect_traits(private_elements)
        self._collect_case_classes(private_elements)
        self._collect_classes(private_elements)
        self._collect_class_members(private_elements)
        self._collect_type_aliases(private_elements)
        self._collect_variables(private_elements)

        return private_elements

    def _collect_objects(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public objects."""
        objects = self.doc.query_opt("objects")
        for node, capture_name in objects:
            if capture_name == "object_name":
                object_def = node.parent
                if object_def:
                    element_info = self.analyze_element(object_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

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

    def _collect_case_classes(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public case classes."""
        case_classes = self.doc.query_opt("case_classes")
        for node, capture_name in case_classes:
            if capture_name == "case_class_name":
                case_class_def = node.parent
                if case_class_def:
                    element_info = self.analyze_element(case_class_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_type_aliases(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public type aliases."""
        type_aliases = self.doc.query_opt("type_aliases")
        for node, capture_name in type_aliases:
            if capture_name == "type_name":
                type_def = node.parent
                if type_def:
                    element_info = self.analyze_element(type_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_variables(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public vals and vars."""
        variables = self.doc.query_opt("variables")
        for node, capture_name in variables:
            if capture_name in ("val_name", "var_name", "given_name"):
                # Navigate to val_definition or var_definition
                var_def = node.parent
                if var_def:
                    element_info = self.analyze_element(var_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_classes(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-public classes."""
        classes = self.doc.query_opt("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                if class_def:
                    element_info = self.analyze_element(class_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_class_members(self, private_elements: List[ElementInfo]) -> None:
        """Collect private class members (fields and methods)."""
        class_members = self.doc.query_opt("class_members")
        for node, capture_name in class_members:
            if capture_name in ("method_name", "field_name"):
                member_def = node.parent  # identifier -> definition
                if member_def:
                    element_info = self.analyze_element(member_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _is_case_class(self, node: Node) -> bool:
        """
        Check if a class definition is a case class.

        Args:
            node: class_definition node

        Returns:
            True if it's a case class
        """
        for child in node.children:
            if child.type == "modifiers":
                modifier_text = self.doc.get_node_text(child)
                if "case" in modifier_text:
                    return True
        return False

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Scala.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "block_comment", "newline", "\n", " ", "\t")
