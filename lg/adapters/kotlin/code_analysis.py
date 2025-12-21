"""
Kotlin-specific implementation of unified code analyzer.
Combines structure and visibility analysis functionality for Kotlin.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple, Dict

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo, FunctionGroup
from ..tree_sitter_support import Node


class KotlinCodeAnalyzer(CodeAnalyzer):
    """Kotlin-specific implementation of unified code analyzer."""

    def determine_element_type(self, node: Node) -> str:
        """
        Determine Kotlin element type based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "object", "property", "lambda"
        """
        node_type = node.type
        
        if node_type == "class_declaration":
            return "class"
        elif node_type == "object_declaration":
            return "object"
        elif node_type == "function_declaration":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "property_declaration":
            return "property"
        elif node_type == "secondary_constructor":
            return "constructor"
        elif node_type == "lambda_literal":
            return "lambda"
        else:
            # Fallback: try to determine from parent context
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Extract Kotlin element name from Tree-sitter node.

        Args:
            node: Tree-sitter node of element

        Returns:
            Element name or None if not found
        """
        # For lambda_literal try to find name from property_declaration
        if node.type == "lambda_literal":
            # Lambda is part of property_declaration: val name = { ... }
            parent = node.parent
            if parent and parent.type == "property_declaration":
                for child in parent.children:
                    if child.type == "variable_declaration":
                        for grandchild in child.children:
                            if grandchild.type == "identifier":
                                return self.doc.get_node_text(grandchild)
            return None  # Anonymous lambda

        # For property_declaration look for variable_declaration
        if node.type == "property_declaration":
            for child in node.children:
                if child.type == "variable_declaration":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)

        # Look for child node with name (identifier)
        for child in node.children:
            if child.type == "identifier":
                return self.doc.get_node_text(child)

        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Determine Kotlin element visibility from modifiers.

        Kotlin rules:
        - private - private
        - protected - protected
        - internal - internal (module)
        - public (default) - public

        Args:
            node: Tree-sitter node of element

        Returns:
            Visibility level of element
        """
        # Look for visibility modifier among child nodes
        for child in node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    if modifier_child.type == "visibility_modifier":
                        modifier_text = self.doc.get_node_text(modifier_child)
                        if modifier_text == "private":
                            return Visibility.PRIVATE
                        elif modifier_text == "protected":
                            return Visibility.PROTECTED
                        elif modifier_text == "internal":
                            return Visibility.INTERNAL
                        elif modifier_text == "public":
                            return Visibility.PUBLIC

        # In Kotlin, all elements are public by default
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Determine Kotlin element export status.

        Rules:
        - Methods inside classes/objects are NOT directly exportable
        - Top-level functions, classes, objects are exported if public/internal
        - private elements are not exported

        Args:
            node: Tree-sitter node of element

        Returns:
            Export status of element
        """
        # If this is method/property inside class, it is NOT directly exported
        if node.type == "function_declaration" and self.is_method_context(node):
            return ExportStatus.NOT_EXPORTED

        if node.type == "property_declaration" and self.is_inside_class(node):
            return ExportStatus.NOT_EXPORTED

        # For top-level elements check visibility
        visibility = self.determine_visibility(node)

        # In Kotlin public and internal elements are exported
        if visibility in (Visibility.PUBLIC, Visibility.INTERNAL):
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Determine if node is a method of Kotlin class or object.

        Args:
            node: Tree-sitter node for analysis

        Returns:
            True if node is a method, False if top-level function
        """
        # Walk up tree looking for class or object
        current = node.parent
        while current:
            if current.type in ("class_declaration", "object_declaration", "class_body"):
                return True
            # Stop at file boundaries
            if current.type in ("source_file",):
                break
            current = current.parent
        return False

    def is_inside_class(self, node: Node) -> bool:
        """
        Check if node is inside class or object.

        Args:
            node: Tree-sitter node for checking

        Returns:
            True if inside class/object
        """
        current = node.parent
        while current:
            if current.type in ("class_declaration", "object_declaration"):
                return True
            if current.type == "source_file":
                break
            current = current.parent
        return False

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Find function_declaration or lambda_literal for given node by walking up tree.

        Args:
            node: Node for searching parent function

        Returns:
            Function definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in ("function_declaration", "lambda_literal"):
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Return node types for wrapped decorated definitions in Kotlin.

        In Kotlin annotations are embedded in modifiers, not wrapping definitions.

        Returns:
            Empty set (no wrapped definitions in Kotlin)
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Return node types for annotations in Kotlin.

        Returns:
            Set of node types
        """
        return {
            "annotation",  # Kotlin @Annotation
        }

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Find all annotations for Kotlin code element.

        In Kotlin annotations are located inside modifiers node.

        Args:
            node: Element node

        Returns:
            List of annotation nodes
        """
        annotations = []

        # Look for modifiers among child nodes
        for child in node.children:
            if child.type == "modifiers":
                # Collect all annotations inside modifiers
                for modifier_child in child.children:
                    if modifier_child.type == "annotation":
                        annotations.append(modifier_child)

        return annotations

    def _group_function_captures(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Kotlin-specific grouping of functions and lambdas.

        Overrides base method for correct handling of lambda_literal.
        """
        function_groups = {}

        # Collect definitions
        for node, capture_name in captures:
            if self.is_function_definition_capture(capture_name):
                element_info = self.analyze_element(node)

                # For lambdas extract body specially
                body_node = None
                strip_range = (0, 0)
                if node.type == "lambda_literal":
                    body_node = self.extract_lambda_body(node)
                    if body_node:
                        strip_range = self.compute_strippable_range(node, body_node)

                function_groups[node] = FunctionGroup(
                    definition=node,
                    element_info=element_info,
                    body_node=body_node,
                    strippable_range=strip_range
                )

        # For normal functions look for bodies using standard logic
        for node, capture_name in captures:
            if self.is_function_body_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    # Only for function_declaration, not for lambda
                    if func_def.type == "function_declaration":
                        old_group = function_groups[func_def]
                        strip_range = self.compute_strippable_range(func_def, node)
                        closing_brace = self._find_closing_brace_byte(node)
                        return_node = self._find_return_statement(node)
                        function_groups[func_def] = FunctionGroup(
                            definition=old_group.definition,
                            element_info=old_group.element_info,
                            name_node=old_group.name_node,
                            body_node=node,
                            strippable_range=strip_range,
                            closing_brace_byte=closing_brace,
                            return_node=return_node
                        )

            elif self.is_function_name_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    old_group = function_groups[func_def]
                    function_groups[func_def] = FunctionGroup(
                        definition=old_group.definition,
                        element_info=old_group.element_info,
                        name_node=node,
                        body_node=old_group.body_node,
                        strippable_range=old_group.strippable_range,
                        closing_brace_byte=old_group.closing_brace_byte,
                        return_node=old_group.return_node
                    )

        return function_groups

    def collect_function_like_elements(self) -> Dict[Node, FunctionGroup]:
        """
        Collect all functions and lambdas from document.

        Returns:
            Dictionary: function_node -> FunctionGroup with function information
        """
        functions = self.doc.query("functions")
        return self._group_function_captures(functions)
    
    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Collect Kotlin-specific private elements.

        Includes object declarations, properties.

        Returns:
            List of Kotlin-specific private elements
        """
        private_elements = []

        # Collect object declarations
        self._collect_objects(private_elements)

        # Collect properties (Kotlin properties)
        self._collect_properties(private_elements)

        # Collect misparsed classes (with multiple annotations)
        self._collect_misparsed_classes(private_elements)

        return private_elements

    def _collect_objects(self, private_elements: List[ElementInfo]) -> None:
        """Collect non-exported object declarations."""
        objects = self.doc.query_opt("objects")
        for node, capture_name in objects:
            if capture_name == "object_name":
                object_def = node.parent
                if object_def:
                    element_info = self.analyze_element(object_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_properties(self, private_elements: List[ElementInfo]) -> None:
        """Collect private/protected properties."""
        properties = self.doc.query_opt("properties")
        for node, capture_name in properties:
            if capture_name == "property_name":
                # Walk up to property_declaration
                property_def = node.parent
                if property_def:
                    property_def = property_def.parent  # variable_declaration -> property_declaration
                if property_def:
                    element_info = self.analyze_element(property_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_misparsed_classes(self, private_elements: List[ElementInfo]) -> None:
        """
        Collect classes that Tree-sitter misparsed.

        Issue: Tree-sitter Kotlin sometimes misparsed classes with multiple
        annotations on separate lines before visibility modifier.
        Instead of class_declaration creates annotated_expression -> infix_expression.

        This method searches for such constructs directly in text and checks visibility.
        """
        # Look for all "infix_expression" nodes which may be misparsed classes
        def find_infix_expressions(node):
            """Recursively find all infix_expression nodes"""
            results = []
            if node.type == "infix_expression":
                results.append(node)
            for child in node.children:
                results.extend(find_infix_expressions(child))
            return results

        infix_nodes = find_infix_expressions(self.doc.root_node)

        for infix_node in infix_nodes:
            # Get node text
            node_text = self.doc.get_node_text(infix_node)

            # Normalize to string
            if isinstance(node_text, bytes):
                text_str = node_text.decode('utf-8', errors='ignore')
            else:
                text_str = node_text

            # Check if text contains "private class" or "protected class"
            if "private class" not in text_str and "protected class" not in text_str:
                continue

            # This is probably a misparsed class
            # Determine visibility from text
            if "private" in text_str:
                visibility = Visibility.PRIVATE
            elif "protected" in text_str:
                visibility = Visibility.PROTECTED
            else:
                continue  # Not private/protected - skip

            # Extract class name (after "class ")
            import re
            class_match = re.search(r'\b(?:private|protected)\s+class\s+(\w+)', text_str)
            if class_match:
                class_name = class_match.group(1)
            else:
                class_name = None

            # Find annotations before this node
            decorators = self._find_annotations_before_node(infix_node)

            # Create ElementInfo
            element_info = ElementInfo(
                node=infix_node,
                element_type="class",
                name=class_name,
                visibility=visibility,
                export_status=ExportStatus.NOT_EXPORTED,
                is_method=False,
                decorators=decorators
            )

            private_elements.append(element_info)

    def _find_annotations_before_node(self, node: Node) -> List[Node]:
        """
        Find annotations before node by walking up annotated_expression tree.

        Args:
            node: Node for finding annotations

        Returns:
            List of annotation nodes
        """
        annotations = []

        # Walk up parents collecting annotated_expression
        current = node.parent
        while current and current.type == "annotated_expression":
            # Look for annotations among children of annotated_expression
            for child in current.children:
                if child.type == "annotation":
                    annotations.insert(0, child)  # Insert at start for correct order
            current = current.parent

        return annotations

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Kotlin.

        Args:
            node: Tree-sitter node for checking

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "multiline_comment", "newline", "\n", " ", "\t")

    def extract_lambda_body(self, lambda_node: Node) -> Optional[Node]:
        """
        Extract Kotlin lambda function body.

        Structure of lambda_literal:
        - { opening brace
        - lambda_parameters? (optional)
        - -> (optional, if parameters present)
        - body (statements)
        - } closing brace

        Args:
            lambda_node: lambda_literal node

        Returns:
            Node representing lambda body (or None for single-line)
        """
        if lambda_node.type != "lambda_literal":
            return None

        # For single-line lambdas don't strip body
        start_line, end_line = self.doc.get_line_range(lambda_node)
        if start_line == end_line:
            return None  # Single-line lambda, don't strip

        # Create synthetic node for lambda body
        # Body starts after -> (if present) or after {
        body_start_idx = 0

        for i, child in enumerate(lambda_node.children):
            if child.type == "->":
                body_start_idx = i + 1
                break
            elif child.type == "{":
                body_start_idx = i + 1

        # Body ends before }
        body_end_idx = len(lambda_node.children) - 1
        for i in range(len(lambda_node.children) - 1, -1, -1):
            if lambda_node.children[i].type == "}":
                body_end_idx = i
                break

        # If no body (empty lambda or only parameters)
        if body_start_idx >= body_end_idx:
            return None

        # Return range from first statement to last
        first_statement = lambda_node.children[body_start_idx]
        last_statement = lambda_node.children[body_end_idx - 1]

        # Create synthetic wrapper node
        class LambdaBodyRange:
            def __init__(self, start_node, end_node):
                self.start_byte = start_node.start_byte
                self.end_byte = end_node.end_byte
                self.start_point = start_node.start_point
                self.end_point = end_node.end_point
                self.type = "lambda_body"

        return LambdaBodyRange(first_statement, last_statement)

    def compute_strippable_range(self, func_def: Node, body_node: Node) -> Tuple[int, int]:
        """
        Compute strippable range for Kotlin function body.

        Handles:
        - Nested structure: function_body -> block -> statements
        - KDoc preservation inside body
        - Brace exclusion for proper AST after stripping

        Args:
            func_def: Function definition node
            body_node: Function body node (function_body wrapper)

        Returns:
            Tuple of (start_byte, end_byte) for stripping
        """
        # For lambda, body_node is LambdaBodyRange (synthetic), return its byte range
        if func_def.type == "lambda_literal":
            return (body_node.start_byte, body_node.end_byte)

        # Find the inner block node (function_body -> block)
        block_node = self._get_inner_block(body_node)
        if not block_node:
            return (body_node.start_byte, body_node.end_byte)

        # Check for KDoc inside function body
        kdoc_inside = self._find_kdoc_in_body(body_node)

        if kdoc_inside is None:
            # No KDoc inside - use inner content range (exclude braces)
            return self._compute_inner_body_range(block_node)

        # KDoc inside body - strip only after it
        # Find first non-whitespace content after KDoc
        start_byte = self._find_next_content_byte(kdoc_inside.end_byte)
        # End before closing brace
        inner_start, inner_end = self._compute_inner_body_range(block_node)
        return (start_byte, inner_end)

    def _get_inner_block(self, body_node: Node) -> Optional[Node]:
        """
        Get the inner block node from function_body wrapper.

        Kotlin AST structure: function_body -> block -> statements
        """
        for child in body_node.children:
            if child.type == "block":
                return child
        return None

    def _find_kdoc_in_body(self, body_node: Node) -> Optional[Node]:
        """
        Find KDoc comment at start of function body.

        Args:
            body_node: function_body node

        Returns:
            block_comment node with KDoc or None
        """
        # Function body in Kotlin is function_body -> block -> statements
        block_node = None
        for child in body_node.children:
            if child.type == "block":
                block_node = child
                break

        if not block_node:
            return None

        # Look for first block_comment in block
        for child in block_node.children:
            if child.type in ("{", "}"):
                continue

            if child.type == "block_comment":
                text = self.doc.get_node_text(child)
                if text.startswith("/**"):
                    return child

            # If we encounter something else - KDoc should be first
            break

        return None

    def _find_next_content_byte(self, pos: int) -> int:
        """
        Find start of line containing first non-whitespace after position.

        For proper indentation in placeholders, we need to return the start of
        the line, not the first non-whitespace character.
        """
        text = self.doc.text
        # Find newline after current position
        newline_pos = text.find('\n', pos)
        if newline_pos == -1:
            return pos
        # Return position after newline (start of next line)
        return newline_pos + 1

    def _find_closing_brace_byte(self, body_node: Node) -> Optional[int]:
        """
        Find closing brace byte position for Kotlin function body.

        Handles nested structure: function_body -> block -> {statements}
        """
        # For Kotlin, body_node is function_body, need to look in inner block
        block_node = self._get_inner_block(body_node)
        if block_node:
            return super()._find_closing_brace_byte(block_node)
        return None

    def _find_return_statement(self, body_node: Node) -> Optional[Node]:
        """
        Find return statement at the end of Kotlin function body.

        Handles nested structure: function_body -> block -> {statements}
        """
        # For Kotlin, body_node is function_body, need to look in inner block
        block_node = self._get_inner_block(body_node)
        if block_node:
            return super()._find_return_statement(block_node)
        return None

