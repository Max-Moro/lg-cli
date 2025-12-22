"""
C-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for C.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


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

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect C-specific private elements.

        Note: Functions are already collected by base CodeAnalyzer.
        This method collects only C-specific elements:
        - static declarations (not function definitions)
        - typedefs (which include typedef enum, typedef struct, typedef union)

        We don't collect enums/structs/unions separately because in C they're
        typically wrapped in typedefs and would be duplicated.

        Returns:
            List of C-specific private elements
        """
        private_elements = []

        # C-specific elements (functions already collected by base)
        self._collect_static_declarations(private_elements)
        self._collect_typedefs(private_elements)

        return private_elements

    def _collect_static_functions(self, private_elements: List[ElementInfo]) -> None:
        """Collect static functions (file-scope)."""
        functions = self.doc.query_opt("functions")
        for node, capture_name in functions:
            if capture_name == "function_definition":
                element_info = self.analyze_element(node)
                if not element_info.in_public_api:
                    private_elements.append(element_info)

    def _collect_static_declarations(self, private_elements: List[ElementInfo]) -> None:
        """Collect static function declarations and static variable declarations."""
        declarations = self.doc.query_opt("declarations")
        for node, capture_name in declarations:
            if capture_name == "declaration":
                # Only collect if it has static specifier and is not in public API
                if self._has_static_specifier(node):
                    element_info = self.analyze_element(node)
                    if not element_info.in_public_api:
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

    def _collect_typedefs(self, private_elements: List[ElementInfo]) -> None:
        """Collect private typedefs."""
        typedefs = self.doc.query_opt("typedefs")
        seen_positions = set()

        for node, capture_name in typedefs:
            if capture_name == "typedef_name":
                typedef_def = node.parent
                if typedef_def:
                    # Deduplicate by position (C grammar may return same typedef twice)
                    pos_key = (typedef_def.start_byte, typedef_def.end_byte)
                    if pos_key in seen_positions:
                        continue
                    seen_positions.add(pos_key)

                    element_info = self.analyze_element(typedef_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_structs(self, private_elements: List[ElementInfo]) -> None:
        """Collect private named struct declarations."""
        structs = self.doc.query_opt("classes")
        for node, capture_name in structs:
            if capture_name == "struct_name":
                struct_def = node.parent
                if struct_def:
                    element_info = self.analyze_element(struct_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_unions(self, private_elements: List[ElementInfo]) -> None:
        """Collect private named union declarations."""
        unions = self.doc.query_opt("classes")  # unions are in "classes" query
        for node, capture_name in unions:
            if capture_name == "union_name":
                union_def = node.parent
                if union_def:
                    element_info = self.analyze_element(union_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

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
