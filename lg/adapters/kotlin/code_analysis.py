"""
Kotlin-specific implementation of unified code analyzer.
Combines structure and visibility analysis functionality for Kotlin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Dict

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo, FunctionGroup
from ..tree_sitter_support import Node, TreeSitterDocument

if TYPE_CHECKING:
    from ..optimizations.public_api.profiles import LanguageElementProfiles


class KotlinCodeAnalyzer(CodeAnalyzer):
    """Kotlin-specific implementation of unified code analyzer."""

    # Kotlin-specific node types that represent function-like elements
    FUNCTION_DEFINITION_TYPES = {
        "function_declaration",
        "anonymous_initializer",
        "secondary_constructor",
        "getter",
        "setter",
        "lambda_literal",
    }

    def determine_element_type(self, node: Node) -> str:
        """
        Determine Kotlin element type based on node structure.

        Args:
            node: Tree-sitter node

        Returns:
            String with element type: "function", "method", "class", "object", "property", "lambda", etc.
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
        elif node_type == "anonymous_initializer":
            return "init"
        elif node_type == "getter":
            return "getter"
        elif node_type == "setter":
            return "setter"
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
        Find function-like element for given node by walking up tree.

        Supports all Kotlin function-like elements:
        - function_declaration
        - anonymous_initializer (init blocks)
        - secondary_constructor
        - getter
        - setter
        - lambda_literal

        Args:
            node: Node for searching parent function

        Returns:
            Function definition or None if not found
        """
        current = node.parent
        while current:
            if current.type in self.FUNCTION_DEFINITION_TYPES:
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
        For misparsed classes (infix_expression), annotations are in parent annotated_expression nodes.

        Args:
            node: Element node

        Returns:
            List of annotation nodes
        """
        annotations = []

        # Standard case: Look for modifiers among child nodes
        for child in node.children:
            if child.type == "modifiers":
                # Collect all annotations inside modifiers
                for modifier_child in child.children:
                    if modifier_child.type == "annotation":
                        annotations.append(modifier_child)

        # Special case: misparsed classes (infix_expression with "private class" or "protected class")
        if node.type == "infix_expression":
            node_text = self.doc.get_node_text(node)
            if "private class" in node_text or "protected class" in node_text:
                # Walk up parents collecting annotated_expression annotations
                current = node.parent
                while current and current.type == "annotated_expression":
                    # Look for annotations among children of annotated_expression
                    for child in current.children:
                        if child.type == "annotation":
                            annotations.insert(0, child)  # Insert at start for correct order
                    current = current.parent

        return annotations

    # Legacy collection methods removed - using profile-based collection

    def get_element_profiles(self) -> Optional[LanguageElementProfiles]:
        """
        Return Kotlin element profiles for profile-based public API collection.

        Returns:
            LanguageElementProfiles for Kotlin
        """
        from ..optimizations.public_api.language_profiles.kotlin import KOTLIN_PROFILES
        return KOTLIN_PROFILES

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Check if node is whitespace or comment in Kotlin.

        Args:
            node: Tree-sitter node for checking

        Returns:
            True if node is whitespace or comment
        """
        return node.type in ("line_comment", "multiline_comment", "newline", "\n", " ", "\t")

    def compute_strippable_range(self, func_def: Node, body_node: Node) -> Tuple[int, int]:
        """
        Compute the byte range that can be stripped from a Kotlin function body.

        Kotlin AST structure for function bodies:
        - function_declaration/getter/setter: function_body -> block -> { ... }
        - anonymous_initializer/secondary_constructor: block -> { ... }
        - lambda_literal: body content is directly in lambda_literal

        This method handles the nested structure and returns the inner content
        range (after '{' and before '}').

        Args:
            func_def: Function definition node
            body_node: Function body node (function_body or block)

        Returns:
            Tuple of (start_byte, end_byte) for the strippable range
        """
        # Handle lambda_literal specially - body is directly inside
        if func_def.type == "lambda_literal":
            return self._compute_lambda_strippable_range(func_def)

        # For function_body, the actual block is the first child
        if body_node.type == "function_body":
            # function_body -> block -> { content }
            if body_node.children:
                block_node = body_node.children[0]
                if block_node.type == "block":
                    return self._compute_block_inner_range(block_node)

        # For direct block nodes (anonymous_initializer, secondary_constructor)
        if body_node.type == "block":
            return self._compute_block_inner_range(body_node)

        # Fallback to base implementation
        return super().compute_strippable_range(func_def, body_node)

    def _compute_block_inner_range(self, block_node: Node) -> Tuple[int, int]:
        """
        Compute inner content range for a block node, excluding braces.

        Also preserves KDoc comments at the beginning of the block.
        KDoc inside function body is documentation that should be kept.

        Args:
            block_node: Block node with { ... } structure

        Returns:
            Tuple of (start_byte, end_byte) for inner content
        """
        if not block_node.children:
            return (block_node.start_byte, block_node.end_byte)

        first_child = block_node.children[0]
        last_child = block_node.children[-1]

        # Check if block is enclosed in braces
        first_text = self.doc.get_node_text(first_child) if first_child else ""
        last_text = self.doc.get_node_text(last_child) if last_child else ""

        if first_text == "{" and last_text == "}":
            # Start after opening brace
            start_byte = first_child.end_byte
            end_byte = last_child.start_byte

            # Check for KDoc at the beginning of block body
            # KDoc is a multiline_comment starting with /**
            start_byte = self._skip_leading_kdoc(block_node, start_byte, end_byte)

            return (start_byte, end_byte)

        # No braces found, return entire block
        return (block_node.start_byte, block_node.end_byte)

    def _skip_leading_kdoc(self, block_node: Node, start_byte: int, end_byte: int) -> int:
        """
        Skip leading KDoc comment at the beginning of block body.

        KDoc inside function body should be preserved as it's documentation.

        Args:
            block_node: Block node containing the body
            start_byte: Current start byte (after opening brace)
            end_byte: End byte (before closing brace)

        Returns:
            New start_byte after KDoc (if found), or original start_byte
        """
        # Comment node types in Kotlin (Tree-sitter may use different names)
        comment_types = {"multiline_comment", "block_comment"}

        # Look for KDoc among block's children
        for child in block_node.children:
            # Skip the opening brace
            if self.doc.get_node_text(child) == "{":
                continue

            # Check if first content node is a block comment (KDoc)
            if child.type in comment_types:
                comment_text = self.doc.get_node_text(child)
                # KDoc starts with /**
                if comment_text.startswith("/**"):
                    # Skip past this KDoc - strippable content starts after it
                    return child.end_byte

            # If first non-brace child is not a comment, stop looking
            if child.type not in comment_types and child.type != "line_comment":
                break

        return start_byte

    def _find_return_statement(self, body_node: Node) -> Optional[Node]:
        """
        Find return statement at the end of Kotlin function body.

        Kotlin AST structure: function_body -> block -> { ... return_expression }
        This method looks inside the nested block structure.

        Args:
            body_node: Function body node (function_body or block)

        Returns:
            Return statement node if found at end of body, None otherwise
        """
        # For function_body, look inside the nested block
        if body_node.type == "function_body":
            if body_node.children:
                block_node = body_node.children[0]
                if block_node.type == "block":
                    return self._find_return_in_block(block_node)
            return None

        # For direct block nodes (init, constructor)
        if body_node.type == "block":
            return self._find_return_in_block(body_node)

        return None

    def _find_return_in_block(self, block_node: Node) -> Optional[Node]:
        """
        Find return statement as last statement in a block.

        Args:
            block_node: Block node with { ... } structure

        Returns:
            Return statement node if found at end, None otherwise
        """
        if not block_node.children:
            return None

        # Kotlin return types
        return_types = {"return_expression", "return"}

        # Find the last non-brace, non-comment child
        for child in reversed(block_node.children):
            child_text = self.doc.get_node_text(child) if child else ""
            # Skip closing brace
            if child_text == "}":
                continue
            # Skip comments
            if child.type in ("line_comment", "block_comment", "multiline_comment"):
                continue
            # Check if it's a return statement
            if child.type in return_types:
                return child
            # Found a non-return statement at end - no return to preserve
            break

        return None

    def _compute_lambda_strippable_range(self, lambda_node: Node) -> Tuple[int, int]:
        """
        Compute strippable range for lambda_literal.

        Lambda structure: { [params ->] body_content }
        We need to find the content after '->' (if present) or after '{'.

        Args:
            lambda_node: Lambda literal node

        Returns:
            Tuple of (start_byte, end_byte) for strippable range
        """
        if not lambda_node.children:
            return (lambda_node.start_byte, lambda_node.end_byte)

        # Find opening brace and arrow
        opening_brace = None
        arrow_node = None
        closing_brace = None

        for child in lambda_node.children:
            child_text = self.doc.get_node_text(child)
            if child_text == "{":
                opening_brace = child
            elif child_text == "->":
                arrow_node = child
            elif child_text == "}":
                closing_brace = child

        if not opening_brace or not closing_brace:
            return (lambda_node.start_byte, lambda_node.end_byte)

        # Start after '->' if present, otherwise after '{'
        if arrow_node:
            start_byte = arrow_node.end_byte
        else:
            start_byte = opening_brace.end_byte

        end_byte = closing_brace.start_byte

        return (start_byte, end_byte)

    def collect_function_like_elements(self) -> Dict[Node, FunctionGroup]:
        """
        Collect all functions and methods from document.

        Kotlin-specific override to handle lambda_literal which doesn't have
        a separate body node - the lambda itself serves as the body container.

        Returns:
            Dictionary: function_node -> FunctionGroup with function information
        """
        functions = self.doc.query("functions")
        groups = self._group_function_captures(functions)

        # Post-process lambda_literal: they don't have separate body_node in query
        # The lambda itself is the body container
        for func_def, func_group in list(groups.items()):
            if func_def.type == "lambda_literal" and func_group.body_node is None:
                # Lambda uses itself as body container
                element_info = func_group.element_info
                strip_range = self._compute_lambda_strippable_range(func_def)

                # Find closing brace for lambda
                closing_brace = None
                for child in func_def.children:
                    if self.doc.get_node_text(child) == "}":
                        closing_brace = child.start_byte
                        break

                groups[func_def] = FunctionGroup(
                    definition=func_group.definition,
                    element_info=element_info,
                    name_node=func_group.name_node,
                    body_node=func_def,  # Lambda is its own body
                    strippable_range=strip_range,
                    closing_brace_byte=closing_brace,
                    return_node=None
                )

        return groups