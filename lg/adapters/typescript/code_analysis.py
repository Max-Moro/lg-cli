"""
TypeScript-specific implementation of unified code analyzer.
Combines structure analysis and visibility analysis functionality for TypeScript.
"""

from __future__ import annotations

from typing import List, Optional, Set, cast

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class TypeScriptCodeAnalyzer(CodeAnalyzer):
    """TypeScript-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine the type of TypeScript element based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "interface", "type", "enum", "namespace", "import", "field"
        """
        node_type = node.type

        # Direct mapping of node types
        if node_type == "class_declaration":
            return "class"
        elif node_type == "interface_declaration":
            return "interface"
        elif node_type == "type_alias_declaration":
            return "type"
        elif node_type == "enum_declaration":
            return "enum"
        elif node_type == "internal_module":
            return "namespace"
        elif node_type == "import_statement":
            return "import"
        elif node_type in ("function_declaration", "arrow_function"):
            # Determine if it's function or method by context
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "method_definition":
            return "method"
        elif node_type in ("public_field_definition", "field_definition"):
            return "field"
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
        Extract name of TypeScript element from Tree-sitter node.

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

        # Search for child node with function/class/method name
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "property_identifier"):
                return self.doc.get_node_text(child)

        # For some node types, name may be in the name field
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine visibility of TypeScript element by access modifiers.

        TypeScript rules:
        - Elements with 'private' modifier - private
        - Elements with 'protected' modifier - protected
        - Elements with 'public' modifier or no modifier - public

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        node_text = self.doc.get_node_text(node)

        # Search for access modifiers among child nodes
        for child in node.children:
            if child.type == "accessibility_modifier":
                modifier_text = self.doc.get_node_text(child)
                if modifier_text == "private":
                    return Visibility.PRIVATE
                elif modifier_text == "protected":
                    return Visibility.PROTECTED
                elif modifier_text == "public":
                    return Visibility.PUBLIC

        # Fallback: check for modifiers in node text
        if "private " in node_text or node_text.strip().startswith("private "):
            return Visibility.PRIVATE
        if "protected " in node_text or node_text.strip().startswith("protected "):
            return Visibility.PROTECTED

        # If no modifier found, element is public by default
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine export status of TypeScript element.

        Rules:
        - Methods inside classes are NOT considered exported
        - Top-level functions, classes, interfaces are exported if they have export
        - Private/protected methods are never exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # If this is a method inside a class, it's NOT exported directly
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
        Determine if node is a method of TypeScript class.

        Args:
            node: Tree-sitter node to analyze

        Returns:
            True if node is class method, False if top-level function
        """
        # Walk up the tree looking for class definition
        current = node.parent
        while current:
            if current.type in ("class_declaration", "class_body"):
                return True
            # Stop at module/file boundaries
            if current.type in ("program", "source_file"):
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
            if current.type in ("function_declaration", "method_definition", "arrow_function"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in TypeScript.

        Returns:
            Set of node types
        """
        return {
            "decorated_definition",    # TypeScript decorators
            "decorator_list",         # Alternative naming
        }

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for individual decorators in TypeScript.

        Returns:
            Set of node types
        """
        return {
            "decorator",              # TypeScript @decorator
            "decorator_expression",   # TypeScript decorator expressions
        }

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect TypeScript-specific private elements.

        Note: Classes, interfaces, types, and methods are already collected by base CodeAnalyzer.
        This method collects only TypeScript-specific elements:
        - namespaces
        - enums
        - class fields (properties)
        - imports
        - variables

        Returns:
            List of TypeScript-specific private elements
        """
        private_elements = []

        # TypeScript-specific elements (classes/interfaces/methods already collected by base)
        self._collect_namespaces(private_elements)
        self._collect_enums(private_elements)
        self._collect_class_fields(private_elements)
        self._collect_imports(private_elements)
        self._collect_variables(private_elements)

        return private_elements
    
    def _collect_namespaces(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported namespaces."""
        namespaces = self.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                if namespace_def:
                    element_info = self.analyze_element(namespace_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_namespace_members(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported members inside exported namespaces."""
        namespaces = self.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                if namespace_def:
                    namespace_info = self.analyze_element(namespace_def)
                    # Only process members of EXPORTED namespaces
                    if namespace_info.is_exported:
                        # Find functions and variables inside this namespace
                        self._collect_non_exported_namespace_members(namespace_def, private_elements)

    def _collect_non_exported_namespace_members(self, namespace_node: Node, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported members of a namespace."""
        # Find statement_block body of namespace
        namespace_body = None
        for child in namespace_node.children:
            if child.type == "statement_block":
                namespace_body = child
                break

        if not namespace_body:
            return

        # Iterate through children of namespace body
        for child in namespace_body.children:
            # Check for function_declaration
            if child.type == "function_declaration":
                # Check if it's exported (has 'export' modifier)
                if not self._has_export_keyword(child):
                    element_info = self.analyze_element(child)
                    private_elements.append(element_info)
            # Check for variable_declaration (const/let/var)
            elif child.type == "variable_declaration":
                if not self._has_export_keyword(child):
                    element_info = self.analyze_element(child)
                    private_elements.append(element_info)
            # For export statements, their children are exported - skip

    def _has_export_keyword(self, node: Node) -> bool:
        """Check if node text starts with 'export'."""
        node_text = self.doc.get_node_text(node).strip()
        return node_text.startswith("export ")

    def _collect_enums(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported enums."""
        enums = self.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                if enum_def:
                    element_info = self.analyze_element(enum_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_class_fields(self, private_elements: List[ElementInfo]) -> None:
        """Collect private/protected class fields (properties only, not methods)."""
        class_fields = self.doc.query_opt("class_fields")
        for node, capture_name in class_fields:
            # Only collect fields, not methods (methods collected by base)
            if capture_name == "field_name":
                field_def = node.parent
                if field_def:
                    element_info = self.analyze_element(field_def)
                    if not element_info.in_public_api:
                        # Extend range to include semicolon if present
                        element_with_punctuation = self._extend_range_for_semicolon(field_def)
                        # Create new ElementInfo with extended node (duck-typed, cast for type checker)
                        element_info = ElementInfo(
                            node=cast(Node, element_with_punctuation),
                            element_type=element_info.element_type,
                            name=element_info.name,
                            visibility=element_info.visibility,
                            export_status=element_info.export_status,
                            is_method=element_info.is_method,
                            decorators=element_info.decorators
                        )
                        private_elements.append(element_info)

    def _collect_imports(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-re-exported imports."""
        imports = self.doc.query_opt("imports")
        for node, capture_name in imports:
            if capture_name == "import":
                # In public API mode, side-effect imports must be PRESERVED (they can change global state)
                import_text = self.doc.get_node_text(node)
                side_effect = ("from" not in import_text) and ("{" not in import_text) and ("* as" not in import_text)
                if side_effect:
                    # Don't add to private_elements -> don't remove
                    continue
                # Otherwise - regular import; if not participating in public API directly, can be removed
                element_info = self.analyze_element(node)
                private_elements.append(element_info)

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

                    # For top-level variables check visibility and export
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

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
            # Simple check for export at start of line
            if line_text.startswith('export '):
                return True

        return False

    def _extend_range_for_semicolon(self, node):
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
    
    def _create_extended_range_node(self, original_node, semicolon_node):
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

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in TypeScript.

        Args:
            node: Tree-sitter node to check

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("comment", "line_comment", "block_comment", "newline", "\n", " ", "\t")
