"""
C-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for C.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node

if TYPE_CHECKING:
    from ..optimizations.public_api.profiles import LanguageElementProfiles


class CCodeAnalyzer(CodeAnalyzer):
    """C-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of C element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "struct", "union", "enum", "typedef"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "function_definition":
            return "function"
        elif node_type == "struct_specifier":
            return "struct"
        elif node_type == "union_specifier":
            return "union"
        elif node_type == "enum_specifier":
            return "enum"
        elif node_type == "type_definition":
            return "typedef"
        elif node_type == "declaration":
            # Could be function declaration or variable
            return "declaration"
        else:
            return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract name of C element from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # For function definitions, look for function_declarator
        if node.type == "function_definition":
            for child in node.children:
                if child.type in ("function_declarator", "pointer_declarator"):
                    name = self._extract_function_name(child)
                    if name:
                        return name

        # For type definitions
        if node.type == "type_definition":
            for child in reversed(node.children):
                if child.type == "type_identifier":
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
        Determine visibility of C element.

        C doesn't have explicit visibility modifiers.
        Convention-based approach:
        - static functions/variables - private (file scope)
        - extern or no specifier - public (external linkage)

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # Check for static storage class specifier
        if self._has_static_specifier(node):
            return Visibility.PRIVATE

        # Default: public (external linkage)
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of C element.

        C rules:
        - static functions/variables are not exported
        - Functions/variables without static are exported
        - Structs/enums/typedefs are considered exported if they have external linkage
        - Types with Internal* or _* prefix are considered internal (not exported)

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Header files - all elements are exported (public API)
        if self.doc.ext in ('h', 'hpp', 'hh', 'hxx'):
            return ExportStatus.EXPORTED

        # Static elements are not exported
        if self._has_static_specifier(node):
            return ExportStatus.NOT_EXPORTED

        # Check naming convention for typedef and type definitions
        if node.type in ("type_definition", "struct_specifier", "enum_specifier", "union_specifier"):
            element_name = self.extract_element_name(node)
            if self._is_internal_by_naming(element_name):
                return ExportStatus.NOT_EXPORTED

        # Functions and top-level declarations are exported
        if node.type in ("function_definition", "declaration"):
            return ExportStatus.EXPORTED

        # Structs, enums, typedefs are exported
        if node.type in ("struct_specifier", "enum_specifier", "type_definition", "union_specifier"):
            return ExportStatus.EXPORTED

        return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is inside a struct (C doesn't have methods).

        Args:
            node: Tree-sitter node to analyze

        Returns:
            Always False for C (no methods)
        """
        # C doesn't have methods, only functions
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
        Return node types for wrapped decorated definitions in C.

        C doesn't have decorators.

        Returns:
            Empty set
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in C.

        C doesn't have decorators.

        Returns:
            Empty set
        """
        return set()

    # Legacy collection methods removed - using profile-based collection

    def _has_static_specifier(self, node: Node) -> bool:
        """Check if node has static storage class specifier."""
        for child in node.children:
            if child.type == "storage_class_specifier":
                if "static" in self.doc.get_node_text(child):
                    return True
        return False

    def _extract_function_name(self, declarator: Node) -> Optional[str]:
        """
        Extract function name from function_declarator or pointer_declarator.

        Args:
            declarator: Declarator node

        Returns:
            Function name or None
        """
        for child in declarator.children:
            if child.type == "identifier":
                return self.doc.get_node_text(child)
            elif child.type in ("function_declarator", "pointer_declarator"):
                # Recursive search in nested declarators
                name = self._extract_function_name(child)
                if name:
                    return name
        return None

    def get_element_profiles(self) -> Optional[LanguageElementProfiles]:
        """
        Return C element profiles for profile-based public API collection.

        Returns:
            LanguageElementProfiles for C
        """
        from ..optimizations.public_api.language_profiles.c import C_PROFILES
        return C_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in C.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")

    def _is_internal_by_naming(self, name: Optional[str]) -> bool:
        """
        Check if name follows internal naming convention.

        Convention:
        - Names starting with 'Internal' are considered internal
        - Names starting with '_' are considered internal

        Args:
            name: Element name to check

        Returns:
            True if name follows internal convention
        """
        if not name:
            return False
        return name.startswith('Internal') or name.startswith('_')
