"""
Java-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Java.
"""

from __future__ import annotations

from typing import Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus
from ..optimizations.public_api import LanguageElementProfiles
from ..tree_sitter_support import Node


class JavaCodeAnalyzer(CodeAnalyzer):
    """Java-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of Java element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "interface", "enum", "annotation", "field", "constructor"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "class_declaration":
            return "class"
        elif node_type == "interface_declaration":
            return "interface"
        elif node_type == "enum_declaration":
            return "enum"
        elif node_type == "annotation_type_declaration":
            return "annotation"
        elif node_type == "method_declaration":
            return "method"
        elif node_type == "constructor_declaration":
            return "constructor"
        elif node_type == "field_declaration":
            return "field"
        elif node_type == "local_variable_declaration":
            return "field"
        else:
            # Fallback: determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of Java element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # Special handling for field_declaration and local_variable_declaration
        if node.type in ("field_declaration", "local_variable_declaration"):
            # Search for variable_declarator with name
            for child in node.children:
                if child.type == "variable_declarator":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)

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
        Determine visibility of Java element by access modifiers.

        Java rules:
        - Elements with 'private' modifier - private
        - Elements with 'protected' modifier - protected
        - Elements with 'public' modifier - public
        - Interface members without modifier - public (implicit)
        - No modifier (package-private) - internal

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # Search for modifiers node
        for child in node.children:
            if child.type == "modifiers":
                modifier_text = self.doc.get_node_text(child)
                if "private" in modifier_text:
                    return Visibility.PRIVATE
                elif "protected" in modifier_text:
                    return Visibility.PROTECTED
                elif "public" in modifier_text:
                    return Visibility.PUBLIC

        # Special case: interface members are implicitly public
        if self._is_interface_member(node):
            return Visibility.PUBLIC

        # No explicit modifier - package-private (internal)
        return Visibility.INTERNAL

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of Java element.

        Rules:
        - Methods, fields, and constructors inside classes are NOT exported directly
        - Top-level public local variables are exported (public static final)
        - Top-level public classes/interfaces are exported
        - Package-private, protected, and private elements are not exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Methods, fields, and constructors are never directly exported
        if node.type in ("method_declaration", "field_declaration", "constructor_declaration"):
            return ExportStatus.NOT_EXPORTED

        # For local variables (top-level fields), check visibility
        if node.type == "local_variable_declaration":
            visibility = self.determine_visibility(node)
            if visibility == Visibility.PUBLIC:
                return ExportStatus.EXPORTED
            else:
                return ExportStatus.NOT_EXPORTED

        # For top-level classes/interfaces, check visibility
        visibility = self.determine_visibility(node)

        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method of Java class.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is class method, False if top-level
        """
        # Walk up the tree looking for class/interface/enum
        current = node.parent
        while current:
            if current.type in ("class_declaration", "interface_declaration", "enum_declaration", "class_body"):
                return True
            # Stop at file boundaries
            if current.type in ("program", "source_file"):
                break
            current = current.parent
        return False

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find method_declaration for given node by walking up the tree.

        Args:
            node: Node to find parent method

        Returns:
            Method definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in ("method_declaration", "constructor_declaration"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in Java.

        Java doesn't have decorator wrappers like Python.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual annotations in Java.

        Returns:
            Set of node types
        """
        return {
            "annotation",
            "marker_annotation",
        }


    def _has_static_modifier(self, node: Node) -> bool:
        """Check if node has static modifier."""
        for child in node.children:
            if child.type == "modifiers":
                modifier_text = self.doc.get_node_text(child)
                if "static" in modifier_text:
                    return True
        return False

    def _is_interface_member(self, node: Node) -> bool:
        """
        Check if node is a member of an interface.

        In Java, interface members (methods and fields) are implicitly public.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside an interface
        """
        current = node.parent
        while current:
            if current.type == "interface_declaration":
                return True
            # Stop at class boundaries (nested interfaces)
            if current.type in ("class_declaration", "enum_declaration"):
                return False
            # Stop at file boundaries
            if current.type in ("program", "source_file"):
                break
            current = current.parent
        return False

    def _is_inside_method_or_constructor(self, node: Node) -> bool:
        """
        Check if node is inside a method or constructor body.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside method/constructor
        """
        current = node.parent
        while current:
            # Found method or constructor body - node is inside
            if current.type in ("method_declaration", "constructor_declaration", "block", "constructor_body"):
                return True
            # Stop at class boundaries (don't go beyond class)
            if current.type in ("class_declaration", "interface_declaration", "class_body"):
                return False
            # Stop at file boundaries
            if current.type in ("program", "source_file"):
                break
            current = current.parent
        return False

    def get_element_profiles(self) -> LanguageElementProfiles:
        """Return Java element profiles."""
        from ..optimizations.public_api.language_profiles.java import JAVA_PROFILES
        return JAVA_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Java.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "block_comment", "newline", "\n", " ", "\t")
