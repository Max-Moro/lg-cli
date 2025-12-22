"""
Scala-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for Scala.
"""

from __future__ import annotations

from typing import Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus
from ..optimizations.public_api import LanguageElementProfiles
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

    def get_element_profiles(self) -> LanguageElementProfiles:
        """
        Return Scala element profiles.

        Returns:
            Scala element profiles for profile-based collection
        """
        from ..optimizations.public_api.language_profiles.scala import SCALA_PROFILES
        return SCALA_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Scala.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "block_comment", "newline", "\n", " ", "\t")
