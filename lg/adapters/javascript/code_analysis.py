"""
JavaScript-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for JavaScript.
"""

from __future__ import annotations

from typing import Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node
from ..optimizations.public_api import LanguageElementProfiles


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
        elif node_type == "field_definition":
            return "field"
        elif node_type == "variable_declaration":
            return "variable"
        elif node_type == "import_statement":
            return "import"
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
            if child.type in ("identifier", "property_identifier", "private_property_identifier"):
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
        - Methods inside exported object literals (namespace-like exports) are exported
        - Methods inside classes are NOT exported directly
        - Elements referenced in default exports are exported
        - Top-level functions, classes, variables are exported if they have export keyword
        - Private elements are never exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # Special case: methods in exported object literals (namespace exports)
        # e.g., export const Utils = { formatName() {} }
        if node.type == "method_definition":
            if self._is_in_exported_object_literal(node):
                # Still respect privacy conventions (methods starting with _)
                visibility = self.determine_visibility(node)
                if visibility == Visibility.PRIVATE:
                    return ExportStatus.NOT_EXPORTED
                else:
                    return ExportStatus.EXPORTED
            else:
                # Regular class methods are not exported directly
                return ExportStatus.NOT_EXPORTED

        # Check if this element is a default export
        element_name = self.extract_element_name(node)
        if element_name:
            default_exports = self._find_default_exports()
            if element_name in default_exports:
                return ExportStatus.EXPORTED

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

    def analyze_element(self, node: Node) -> ElementInfo:
        """
        Override to extend range for fields to include semicolons.

        Args:
            node: Tree-sitter node of element

        Returns:
            ElementInfo with potentially extended node range for fields
        """
        # Get standard ElementInfo
        element_info = super().analyze_element(node)

        # For fields, extend range to include trailing semicolon
        if element_info.element_type == "field":
            extended_node = self._extend_range_for_semicolon(node)
            # Create new ElementInfo with extended node
            from ..code_analysis import ElementInfo as EI
            element_info = EI(
                node=extended_node,
                element_type=element_info.element_type,
                name=element_info.name,
                visibility=element_info.visibility,
                export_status=element_info.export_status,
                is_method=element_info.is_method,
                decorators=element_info.decorators
            )

        return element_info

    def _extend_range_for_semicolon(self, node: Node) -> Node:
        """
        Extend node range to include trailing semicolon if present.

        Args:
            node: Tree-sitter node

        Returns:
            Node with extended range or original node
        """
        # Check if there's a semicolon right after this node
        parent = node.parent
        if not parent:
            return node

        # Find position of this node among siblings
        siblings = parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling == node:
                node_index = i
                break

        if node_index is None:
            return node

        # Check if next sibling is a semicolon
        if node_index + 1 < len(siblings):
            next_sibling = siblings[node_index + 1]
            if (next_sibling.type == ";" or
                self.doc.get_node_text(next_sibling).strip() == ";"):
                # Create synthetic range that includes the semicolon
                return self._create_extended_range_node(node, next_sibling)

        return node

    def _create_extended_range_node(self, original_node: Node, semicolon_node: Node) -> Node:
        """
        Create synthetic node-like object with extended range.

        Args:
            original_node: Original node
            semicolon_node: Semicolon node

        Returns:
            Object with extended range
        """
        class ExtendedRangeNode:
            def __init__(self, start_node, end_node):
                self.start_byte = start_node.start_byte
                self.end_byte = end_node.end_byte
                self.start_point = start_node.start_point
                self.end_point = end_node.end_point
                self.type = start_node.type
                self.parent = start_node.parent
                # Copy other frequently used attributes
                for attr in ['children', 'text']:
                    if hasattr(start_node, attr):
                        setattr(self, attr, getattr(start_node, attr))

        return ExtendedRangeNode(original_node, semicolon_node)

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

    def _find_default_exports(self) -> Set[str]:
        """
        Find all default export identifiers in the file.

        For cases like:
            class UserManager {}
            export default UserManager;

        Returns:
            Set of identifiers that are default exported
        """
        default_exports = set()

        # Query for all export statements
        exports = self.doc.query_opt("exports")
        for node, capture_name in exports:
            if node.type == "export_statement":
                # Check if this is a default export
                has_default = False
                identifier = None

                for child in node.children:
                    if child.type == "default":
                        has_default = True
                    elif child.type == "identifier":
                        identifier = self.doc.get_node_text(child)

                if has_default and identifier:
                    default_exports.add(identifier)

        return default_exports

    def _is_in_exported_object_literal(self, node: Node) -> bool:
        """
        Check if a node (typically method_definition) is inside an object literal
        that is the value of an exported variable.

        Example:
            export const Utils = {
                formatName() {}  <- this method should be considered exported
            };

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is inside an exported object literal
        """
        # Walk up to find if we're inside an object
        current = node.parent
        object_node = None

        while current:
            if current.type == "object":
                object_node = current
                break
            # Don't go past program level
            if current.type in ("program", "source_file"):
                break
            current = current.parent

        if not object_node:
            return False

        # Now check if this object is the value of an exported variable
        # Tree: export_statement -> lexical_declaration -> variable_declarator -> object
        current = object_node.parent
        if current and current.type == "variable_declarator":
            current = current.parent  # variable_declarator -> lexical_declaration
            if current and current.type in ("lexical_declaration", "variable_declaration"):
                current = current.parent  # lexical_declaration -> export_statement
                if current and current.type == "export_statement":
                    return True

        return False

    def get_element_profiles(self) -> LanguageElementProfiles:
        """
        Return JavaScript element profiles for profile-based public API collection.

        Returns:
            LanguageElementProfiles for JavaScript
        """
        from ..optimizations.public_api.language_profiles.javascript import JAVASCRIPT_PROFILES
        return JAVASCRIPT_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in JavaScript.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
