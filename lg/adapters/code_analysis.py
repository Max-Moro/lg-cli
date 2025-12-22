"""
Unified code analysis system for language adapters.
Combines structure analysis and visibility analysis into a single component without duplication.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from .tree_sitter_support import Node, TreeSitterDocument

if TYPE_CHECKING:
    from .optimizations.public_api.profiles import LanguageElementProfiles


# ============= Data models =============

class Visibility(Enum):
    """Visibility levels for code elements."""
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"


class ExportStatus(Enum):
    """Export statuses for elements."""
    EXPORTED = "exported"
    NOT_EXPORTED = "not_exported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ElementInfo:
    """Complete information about a code element."""
    node: Node
    element_type: str           # "function", "method", "class", "interface", etc.
    name: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    export_status: ExportStatus = ExportStatus.UNKNOWN
    is_method: bool = False
    decorators: List[Node] = None

    def __post_init__(self):
        if self.decorators is None:
            object.__setattr__(self, 'decorators', [])

    @property
    def is_public(self) -> bool:
        """Is the element public."""
        return self.visibility == Visibility.PUBLIC

    @property
    def is_private(self) -> bool:
        """Is the element private or protected."""
        return self.visibility in (Visibility.PRIVATE, Visibility.PROTECTED)

    @property
    def is_exported(self) -> bool:
        """Is the element exported."""
        return self.export_status == ExportStatus.EXPORTED

    @property
    def in_public_api(self) -> bool:
        """Should the element be included in the public API."""
        # Member types (methods, fields, properties, constructors) use visibility
        # Top-level types (classes, functions, interfaces) use export status
        member_types = {
            "method", "field", "property", "val", "var", "constructor",
            "getter", "setter"
        }

        if self.element_type in member_types:
            # For class/struct members, check visibility (public/private/protected)
            return self.is_public
        else:
            # For top-level declarations, check export status
            return self.is_exported


@dataclass(frozen=True)
class FunctionGroup:
    """Group of nodes related to a single function/method."""
    definition: Node
    element_info: ElementInfo
    name_node: Optional[Node] = None
    body_node: Optional[Node] = None
    # Byte range for stripping (start_byte, end_byte).
    # Computed by language-specific analyzer, accounts for:
    # - Protected content (docstrings) that should be preserved
    # - Leading comments that should be included in stripping
    # - For brace-languages: excludes opening '{' and closing '}'
    # Default (0, 0) means "use entire body_node range"
    strippable_range: Tuple[int, int] = (0, 0)
    # Closing brace position for brace-based languages (byte position).
    # Used by trimmer to preserve closing brace when truncating body.
    # None for languages without braces (e.g., Python).
    closing_brace_byte: Optional[int] = None
    # Return statement node if present at the end of function body.
    # Used by trimmer to preserve return when truncating.
    return_node: Optional[Node] = None

# ============= Main analyzer =============

class CodeAnalyzer(ABC):
    """
    Unified code analyzer.
    Combines functionality for structure analysis and visibility analysis.
    """

    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc

    # ============= Main API =============

    def analyze_element(self, node: Node) -> ElementInfo:
        """
        Complete analysis of a code element.

        Args:
            node: Tree-sitter node for the element

        Returns:
            Complete information about the element
        """
        element_type = self.determine_element_type(node)
        name = self.extract_element_name(node)
        visibility = self.determine_visibility(node)
        export_status = self.determine_export_status(node)
        is_method = self.is_method_context(node)
        decorators = self.find_decorators_for_element(node)

        return ElementInfo(
            node=node,
            element_type=element_type,
            name=name,
            visibility=visibility,
            export_status=export_status,
            is_method=is_method,
            decorators=decorators
        )

    def collect_private_elements_for_public_api(self) -> List[ElementInfo]:
        """
        Collects all private elements for removal in public API mode.

        New implementation via profiles. Falls back to legacy mode if profiles not available.

        Returns:
            List of private elements for removal
        """
        # Get profiles for language
        profiles = self.get_element_profiles()

        if profiles:
            # New path: via PublicApiCollector
            from .optimizations.public_api.collector import PublicApiCollector

            collector = PublicApiCollector(self.doc, self, profiles)
            return collector.collect_private_elements()
        else:
            # Old path: via imperative methods (backward compatibility)
            return self._collect_private_elements_legacy()

    def _collect_private_elements_legacy(self) -> List[ElementInfo]:
        """
        Legacy imperative implementation (for backward compatibility).

        Used when language doesn't have profiles yet.

        Returns:
            List of private elements for removal
        """
        private_elements = []

        # 1. Analyze functions and methods
        self._collect_private_functions_and_methods(private_elements)

        # 2. Analyze classes
        self._collect_classes(private_elements)

        # 3. Analyze interfaces and types (if supported by language)
        self._collect_interfaces_and_types(private_elements)

        # 4. Collect language-specific elements
        language_specific_elements = self.collect_language_specific_private_elements()
        private_elements.extend(language_specific_elements)

        return private_elements

    @abstractmethod
    def get_element_profiles(self) -> Optional[LanguageElementProfiles]:
        """
        Get element profiles for language.

        Returns None to use legacy mode (backward compatibility during migration).

        Returns:
            LanguageElementProfiles or None (if using legacy mode)
        """
        pass

    # ============= Helper methods for collecting private elements =============

    def _collect_private_functions_and_methods(self, private_elements: List[ElementInfo]) -> None:
        """
        Collects private functions and methods for removal in public API mode.

        Args:
            private_elements: List for adding found private elements
        """
        # Get all functions and methods using self-sufficient method
        function_groups = self.collect_function_like_elements()

        for func_def, func_group in function_groups.items():
            element_info = func_group.element_info

            # Universal logic based on element type
            if element_info.is_method:
                # Method is removed if private/protected
                should_remove = not element_info.is_public
            else:  # function, arrow_function, etc.
                # Top-level function is removed if not exported
                should_remove = not element_info.is_exported

            if should_remove:
                private_elements.append(element_info)

    def _collect_classes(self, private_elements: List[ElementInfo]) -> None:
        """
        Collects non-exported classes for removal in public API mode.

        Args:
            private_elements: List for adding found private elements
        """
        # Check classes only if language supports them
        if not self.doc.has_query("classes"):
            return

        classes = self.doc.query("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                if class_def:
                    element_info = self.analyze_element(class_def)

                    # For top-level classes export is the main condition
                    if not element_info.in_public_api:
                        private_elements.append(element_info)

    def _collect_interfaces_and_types(self, private_elements: List[ElementInfo]) -> None:
        """
        Collects non-exported interfaces and types for removal in public API mode.
        This method is applicable to languages with type support (e.g., TypeScript).

        Args:
            private_elements: List for adding found private elements
        """
        # Collect interfaces if supported
        if self.doc.has_query("interfaces"):
            interfaces = self.doc.query("interfaces")
            for node, capture_name in interfaces:
                if capture_name == "interface_name":
                    interface_def = node.parent
                    if interface_def:
                        element_info = self.analyze_element(interface_def)
                        if not element_info.in_public_api:
                            private_elements.append(element_info)

        # Collect type aliases if supported
        if self.doc.has_query("types"):
            types = self.doc.query("types")
            for node, capture_name in types:
                if capture_name == "type_name":
                    type_def = node.parent
                    if type_def:
                        element_info = self.analyze_element(type_def)
                        if not element_info.in_public_api:
                            private_elements.append(element_info)

    # ============= Structural analysis =============

    def _group_function_captures(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Groups Tree-sitter captures by functions/methods.

        Args:
            captures: List of (node, capture_name) from Tree-sitter query

        Returns:
            Dictionary: function_node -> FunctionGroup with function information
        """
        function_groups = {}

        # First collect all function definitions
        for node, capture_name in captures:
            if self.is_function_definition_capture(capture_name):
                element_info = self.analyze_element(node)
                function_groups[node] = FunctionGroup(
                    definition=node,
                    element_info=element_info
                )

        # Then find corresponding bodies and names
        for node, capture_name in captures:
            if self.is_function_body_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    old_group = function_groups[func_def]
                    # Compute strippable range using language-specific logic
                    strip_range = self.compute_strippable_range(func_def, node)
                    # Find closing brace and return statement
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

        # Handle cases where there's no explicit definition in captures
        for node, capture_name in captures:
            if self.is_function_name_capture(capture_name) and node not in function_groups:
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def not in function_groups:
                    element_info = self.analyze_element(func_def)
                    function_groups[func_def] = FunctionGroup(
                        definition=func_def,
                        element_info=element_info,
                        name_node=node
                    )

        return function_groups

    def collect_function_like_elements(self) -> Dict[Node, FunctionGroup]:
        """
        Collect all functions and methods from document.

        Returns:
            Dictionary: function_node -> FunctionGroup with function information
        """
        functions = self.doc.query("functions")
        return self._group_function_captures(functions)

    def compute_strippable_range(self, func_def: Node, body_node: Node) -> Tuple[int, int]:
        """
        Compute the byte range that can be stripped from a function body.

        Default implementation for brace-based languages:
        - Returns inner content range (after '{' and before '}')
        - Preserves structural braces for valid AST after stripping

        Override in language-specific analyzers to handle:
        - Protected content (docstrings) that should be preserved
        - Leading comments that should be included in stripping

        Args:
            func_def: Function definition node
            body_node: Function body node

        Returns:
            Tuple of (start_byte, end_byte) for the strippable range
        """
        return self._compute_inner_body_range(body_node)

    def _compute_inner_body_range(self, body_node: Node) -> Tuple[int, int]:
        """
        Compute inner content range for body node, excluding braces if present.

        For brace-based languages (TypeScript, Java, etc.), body_node is typically
        a statement_block with '{' as first child and '}' as last child.
        This method returns the range of content between these braces.

        Args:
            body_node: Function/method body node

        Returns:
            Tuple of (start_byte, end_byte) for inner content
        """
        if not body_node.children:
            return (body_node.start_byte, body_node.end_byte)

        first_child = body_node.children[0]
        last_child = body_node.children[-1]

        # Check if body is enclosed in braces
        first_text = self.doc.get_node_text(first_child) if first_child else ""
        last_text = self.doc.get_node_text(last_child) if last_child else ""

        if first_text == "{" and last_text == "}":
            # Return range between braces (inner content)
            return (first_child.end_byte, last_child.start_byte)

        # No braces found, return entire body
        return (body_node.start_byte, body_node.end_byte)

    def _find_closing_brace_byte(self, body_node: Node) -> Optional[int]:
        """
        Find closing brace byte position for brace-based function body.

        Args:
            body_node: Function/method body node

        Returns:
            Byte position of closing brace, or None if no brace found
        """
        if not body_node.children:
            return None

        last_child = body_node.children[-1]
        last_text = self.doc.get_node_text(last_child) if last_child else ""

        if last_text == "}":
            return last_child.start_byte

        return None

    def _find_return_statement(self, body_node: Node) -> Optional[Node]:
        """
        Find return statement at the end of function body.

        Searches for the last statement in the body that is a return.
        This is used by trimmer to preserve return when truncating.

        Args:
            body_node: Function/method body node

        Returns:
            Return statement node if found at end of body, None otherwise
        """
        if not body_node.children:
            return None

        # Return statement types across languages
        return_types = {"return_statement", "return", "return_expression"}

        # Find the last non-brace child
        for child in reversed(body_node.children):
            child_text = self.doc.get_node_text(child) if child else ""
            # Skip closing brace
            if child_text == "}":
                continue
            # Skip whitespace/comments if they're nodes
            if child.type in ("comment", "line_comment", "block_comment"):
                continue
            # Check if it's a return statement
            if child.type in return_types:
                return child
            # Found a non-return statement at end - no return to preserve
            break

        return None

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Finds all decorators/annotations for a Python code element.

        Works in two modes:
        1. If the element is wrapped in decorated_definition - extracts decorators from it
        2. Otherwise finds decorators among preceding sibling nodes

        Args:
            node: Node of element (function, class, method)

        Returns:
            List of decorator nodes in order of appearance in code
        """
        decorators = []

        # Mode 1: Check parent for decorated_definition
        parent = node.parent
        if parent and parent.type in self.get_decorated_definition_types():
            # Look for child nodes that are decorators in wrapped definition
            for child in parent.children:
                if child.type in self.get_decorator_types():
                    decorators.append(child)
                elif child == node:
                    # Reached the element itself - stop searching
                    break

        # Mode 2: Find decorators among preceding sibling nodes
        preceding_decorators = self._find_preceding_decorators(node)

        # Combine results, avoiding duplicates
        all_decorators = decorators + [d for d in preceding_decorators if d not in decorators]

        return all_decorators

    def get_element_range_with_decorators(self, elem: ElementInfo) -> Tuple[int, int]:
        """
        Gets the range of element including its decorators/annotations.

        Args:
            elem: Element

        Returns:
            Tuple (start_char, end_char) including all related decorators
        """
        if elem.decorators:
            start_char = self.doc.byte_to_char_position(min(decorator.start_byte for decorator in elem.decorators))
            end_char = self.doc.byte_to_char_position(elem.node.end_byte)
            return start_char, end_char
        else:
            return self.doc.get_node_range(elem.node)

    # ============= Abstract methods for implementation in subclasses =============

    @abstractmethod
    def determine_element_type(self, node: Node) -> str:
        """Determine element type."""
        pass

    @abstractmethod
    def extract_element_name(self, node: Node) -> Optional[str]:
        """Extract element name."""
        pass

    @abstractmethod
    def determine_visibility(self, node: Node) -> Visibility:
        """Determine element visibility."""
        pass

    @abstractmethod
    def determine_export_status(self, node: Node) -> ExportStatus:
        """Determine element export status."""
        pass

    @abstractmethod
    def is_method_context(self, node: Node) -> bool:
        """Determine if element is a class method."""
        pass

    @abstractmethod
    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """Find function definition in parent nodes."""
        pass

    @abstractmethod
    def get_decorated_definition_types(self) -> Set[str]:
        """Return node types for wrapped decorated definitions."""
        pass

    @abstractmethod
    def get_decorator_types(self) -> Set[str]:
        """Return node types for individual decorators."""
        pass

    @abstractmethod
    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """Collect language-specific private elements."""
        pass

    # ============= Helper methods =============

    def is_function_definition_capture(self, capture_name: str) -> bool:
        """Check if capture is a function definition."""
        return capture_name in ("function_definition", "method_definition")

    def is_function_body_capture(self, capture_name: str) -> bool:
        """Check if capture is a function body."""
        return capture_name in ("function_body", "method_body")

    def is_function_name_capture(self, capture_name: str) -> bool:
        """Check if capture is a function name."""
        return capture_name in ("function_name", "method_name")

    def _find_preceding_decorators(self, node: Node) -> List[Node]:
        """Find decorators among preceding sibling nodes."""
        decorators = []

        if not node.parent:
            return decorators

        siblings = node.parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling == node:
                node_index = i
                break

        if node_index is None:
            return decorators

        for i in range(node_index - 1, -1, -1):
            sibling = siblings[i]
            if sibling.type in self.get_decorator_types():
                decorators.insert(0, sibling)
            elif self._is_whitespace_or_comment(sibling):
                continue
            else:
                break

        return decorators

    @abstractmethod
    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """Check if node is whitespace or comment."""
        pass


# ============= Exports =============

__all__ = [
    "CodeAnalyzer",
    "ElementInfo",
    "FunctionGroup",
    "Visibility",
    "ExportStatus"
]
