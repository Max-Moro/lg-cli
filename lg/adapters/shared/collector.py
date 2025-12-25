"""
Universal element collector based on profiles.
Collects CodeElement instances from TreeSitterDocument using LanguageCodeDescriptor.
"""

from __future__ import annotations

from typing import List, Optional

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument
from .descriptor import LanguageCodeDescriptor
from .models import CodeElement
from .profiles import ElementProfile
from .body_range import BodyRangeComputer


class ElementCollector:
    """
    Universal collector for code elements based on profiles.

    Replaces manual _collect_* methods with declarative logic.
    Used by both PublicApiOptimizer and FunctionBodyOptimizer.
    """

    def __init__(self, doc: TreeSitterDocument, descriptor: LanguageCodeDescriptor):
        """
        Initialize collector.

        Args:
            doc: Parsed Tree-sitter document
            descriptor: Language code descriptor with profiles
        """
        self.doc = doc
        self.descriptor = descriptor

        # Cache for collected elements by profile id (supports multiple profiles with same name)
        self._cache: dict[int, List[CodeElement]] = {}

        # Body range computer for function body processing
        self._body_range_computer = BodyRangeComputer(doc, descriptor.comment_types)

    # ============= Main API =============

    def collect_all(self) -> List[CodeElement]:
        """
        Collect all elements from all profiles.

        Returns:
            List of all CodeElement instances found in document.
        """
        all_elements = []
        for profile in self.descriptor.get_profiles():
            elements = self._collect_by_profile(profile)
            all_elements.extend(elements)
        return all_elements

    def collect_by_profile(self, profile_name: str) -> List[CodeElement]:
        """
        Collect elements of a specific profile.

        Args:
            profile_name: Name of profile (e.g., "function", "class")

        Returns:
            List of CodeElement instances matching this profile.
        """
        # Find profile by name
        for profile in self.descriptor.get_profiles():
            if profile.name == profile_name:
                return self._collect_by_profile(profile)
        return []

    def collect_private(self) -> List[CodeElement]:
        """
        Collect only private elements (for public API optimization).

        Returns:
            List of elements where is_public=False, filtered to remove nested.
        """
        all_elements = self.collect_all()
        private_elements = [e for e in all_elements if not e.is_public]
        return self._filter_nested_elements(private_elements)

    def collect_with_bodies(self) -> List[CodeElement]:
        """
        Collect only elements with bodies (for function body optimization).

        Returns:
            List of elements where profile.has_body=True and body_node is not None.
        """
        all_elements = self.collect_all()
        return [e for e in all_elements if e.profile.has_body and e.body_node is not None]

    # ============= Internal methods =============

    def _collect_by_profile(self, profile: ElementProfile) -> List[CodeElement]:
        """
        Collect elements by single profile.

        Uses caching for efficiency.
        """
        # Use profile object id as cache key to handle multiple profiles with same name
        cache_key = id(profile)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        elements = []

        # Execute query
        nodes = self.doc.query_nodes(profile.query, "element")

        for node in nodes:
            # Apply additional_check if specified
            if profile.additional_check:
                if not profile.additional_check(node, self.doc):
                    continue

            # Get definition node (node may be identifier from query)
            element_def = self._get_element_definition(node)
            if not element_def:
                continue

            # Create CodeElement
            element = self._create_element(element_def, profile)
            elements.append(element)

        # Cache and return
        self._cache[cache_key] = elements
        return elements

    def _get_element_definition(self, node: Node) -> Optional[Node]:
        """
        Get definition node for element.

        Query may return identifier, but we need parent definition node.
        """
        # If this is identifier, get parent
        if node.type in ("identifier", "type_identifier", "field_identifier", "property_identifier"):
            return node.parent
        return node

    def _create_element(self, node: Node, profile: ElementProfile) -> CodeElement:
        """
        Create CodeElement from node and profile.
        """
        # Compute adjusted element range if language-specific logic provided
        # (e.g., TypeScript/JavaScript include trailing semicolon)
        element_range = None
        if self.descriptor.compute_element_range:
            element_range = self.descriptor.compute_element_range(node, profile.name, self.doc)

        # Extract name
        name = self._extract_name(node)

        # Determine if public
        is_public = True
        if profile.is_public is not None:
            is_public = profile.is_public(node, self.doc)

        # Find decorators
        decorators = self._find_decorators(node)

        # Extract body info if has_body
        body_node = None
        body_range = None
        docstring_node = None
        return_node = None

        if profile.has_body:
            body_node = self._find_body_node(node, profile)
            if body_node:
                body_range = self._compute_body_range(node, body_node, profile)
                if profile.docstring_extractor:
                    docstring_node = profile.docstring_extractor(body_node, self.doc)
                return_node = self._find_return_statement(body_node)

        return CodeElement(
            profile=profile,
            node=node,
            name=name,
            is_public=is_public,
            body_node=body_node,
            body_range=body_range,
            docstring_node=docstring_node,
            return_node=return_node,
            decorators=decorators,
            element_range=element_range,
        )

    def _extract_name(self, node: Node) -> Optional[str]:
        """
        Extract element name from node.

        Uses descriptor.name_extractor if provided, otherwise default heuristic.
        """
        # Use custom extractor if provided
        if self.descriptor.name_extractor:
            return self.descriptor.name_extractor(node, self.doc)

        # Default heuristic: look for identifier child
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "property_identifier"):
                return self.doc.get_node_text(child)

        # Try field name
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)

        return None

    def _find_decorators(self, node: Node) -> List[Node]:
        """
        Find decorators/annotations attached to element.
        """
        if not self.descriptor.decorator_types:
            return []

        # Use custom decorator_finder if provided (for language-specific AST structures)
        if self.descriptor.decorator_finder:
            return self.descriptor.decorator_finder(node, self.doc, self.descriptor.decorator_types)

        # Standard decorator finding strategies
        decorators = []

        # Check parent for decorated_definition wrapper (Python, TypeScript)
        parent = node.parent
        if parent and parent.type in ("decorated_definition", "decorator_list"):
            for child in parent.children:
                if child.type in self.descriptor.decorator_types:
                    decorators.append(child)
                elif child == node:
                    break

        # Check preceding siblings (common pattern)
        preceding = self._find_preceding_decorators(node)
        decorators.extend(d for d in preceding if d not in decorators)

        return decorators

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

        # Walk backwards through siblings
        for i in range(node_index - 1, -1, -1):
            sibling = siblings[i]
            if sibling.type in self.descriptor.decorator_types:
                decorators.insert(0, sibling)
            elif sibling.type in self.descriptor.comment_types:
                continue  # Skip comments
            elif sibling.type in ("newline", "\n", " ", "\t"):
                continue  # Skip whitespace
            else:
                break  # Stop at other content

        return decorators

    def _find_body_node(self, node: Node, profile: ElementProfile) -> Optional[Node]:
        """
        Find body node for function/method.
        Applies body_resolver if specified to unwrap nested structures.
        """
        # If custom resolver is specified, use it directly
        # (resolver is responsible for finding body in nested structures like arrow functions)
        if profile.body_resolver:
            return profile.body_resolver(node)

        # Use body_query if provided
        if profile.body_query:
            # Query relative to this node
            # For now, use simple child search
            pass

        # Default: look for common body node types
        body_node = None
        for child in node.children:
            if child.type in ("block", "statement_block", "function_body", "body"):
                body_node = child
                break

        # Try field name if not found
        if not body_node:
            body_node = node.child_by_field_name("body")

        return body_node

    def _compute_body_range(
        self,
        func_def: Node,
        body_node: Node,
        profile: ElementProfile
    ) -> tuple[int, int]:
        """
        Compute strippable range for function body.

        Delegates to BodyRangeComputer for actual computation.
        """
        return self._body_range_computer.compute(
            func_def,
            body_node,
            docstring_extractor=profile.docstring_extractor,
            body_range_computer=profile.body_range_computer,
        )

    def _find_return_statement(self, body_node: Node) -> Optional[Node]:
        """
        Find return statement at the end of function body.

        Searches for the last statement in the body that is a return.
        Used by trimmer to preserve return when truncating.

        Args:
            body_node: Function/method body node

        Returns:
            Return statement node if found at end of body, None otherwise
        """
        if not body_node.children:
            return None

        # Return statement types across languages
        return_types = {"return_statement", "return", "return_expression"}

        # Find the last non-brace/non-comment child
        for child in reversed(body_node.children):
            # Skip closing brace
            child_text = self.doc.get_node_text(child) if child else ""
            if child_text == "}":
                continue

            # Skip whitespace/comments
            if child.type in self.descriptor.comment_types:
                continue

            # Check if it's a return statement
            if child.type in return_types:
                return child

            # If we hit a non-return statement, there's no return at the end
            break

        return None

    def _filter_nested_elements(self, elements: List[CodeElement]) -> List[CodeElement]:
        """
        Filter out elements nested inside other elements.

        If a class is private, we don't need to separately remove its private methods.
        """
        if not elements:
            return []

        # Sort by start position
        sorted_elements = sorted(elements, key=lambda e: (e.start_byte, e.end_byte))

        result = []
        for i, elem_i in enumerate(sorted_elements):
            is_nested = False

            for j, elem_j in enumerate(sorted_elements):
                if i == j:
                    continue

                # Check if elem_i is strictly inside elem_j
                if (elem_j.start_byte <= elem_i.start_byte and
                    elem_i.end_byte <= elem_j.end_byte and
                    not (elem_j.start_byte == elem_i.start_byte and elem_j.end_byte == elem_i.end_byte)):
                    is_nested = True
                    break

            if not is_nested:
                result.append(elem_i)

        return result


__all__ = ["ElementCollector"]
