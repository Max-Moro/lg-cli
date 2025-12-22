"""
Universal collector for private elements based on profiles.
Replaces manual _collect_* methods with declarative logic.
"""

from typing import List, Optional

from ...tree_sitter_support import Node, TreeSitterDocument
from ...code_analysis import CodeAnalyzer, ElementInfo
from .profiles import ElementProfile, LanguageElementProfiles


class PublicApiCollector:
    """
    Universal collector for private elements based on profiles.

    Replaces manual _collect_* methods with declarative logic.
    """

    def __init__(
        self,
        doc: TreeSitterDocument,
        analyzer: CodeAnalyzer,
        profiles: LanguageElementProfiles,
    ):
        """
        Initialize collector.

        Args:
            doc: Parsed document
            analyzer: Code analyzer for element analysis
            profiles: Language element profiles
        """
        self.doc = doc
        self.analyzer = analyzer
        self.profiles = profiles.resolve_inheritance()

    def collect_private_elements(self) -> List[ElementInfo]:
        """
        Collect all private elements using profiles.

        Returns:
            List of private elements for removal
        """
        private_elements = []

        for profile in self.profiles:
            elements = self._collect_by_profile(profile)
            private_elements.extend(elements)

        return private_elements

    def _collect_by_profile(self, profile: ElementProfile) -> List[ElementInfo]:
        """
        Collect elements by single profile.

        Args:
            profile: Element profile

        Returns:
            List of private elements of this type
        """
        # Execute query (use query_nodes to get only @element)
        nodes = self.doc.query_nodes(profile.query, "element")

        private_elements = []
        for node in nodes:
            # Optional additional_check
            if profile.additional_check:
                if not profile.additional_check(node, self.doc):
                    continue  # Not an element of this profile

            # Get definition node (node may be identifier)
            element_def = self._get_element_definition(node)
            if not element_def:
                continue

            # Analyze element
            element_info = self.analyzer.analyze_element(element_def)

            # Override element_type with profile name (for metrics)
            # Create new ElementInfo with updated element_type
            element_info = ElementInfo(
                node=element_info.node,
                element_type=profile.name,
                name=element_info.name,
                visibility=element_info.visibility,
                export_status=element_info.export_status,
                is_method=element_info.is_method,
                decorators=element_info.decorators
            )

            # Check if private
            if self._is_private_element(element_def, element_info, profile):
                private_elements.append(element_info)

        return private_elements

    def _get_element_definition(self, node: Node) -> Optional[Node]:
        """
        Get definition node for element.

        Query may return identifier, but we need parent definition node.

        Args:
            node: Node from query result

        Returns:
            Definition node or None
        """
        # If this is identifier, get parent
        if node.type in ("identifier", "type_identifier", "field_identifier"):
            return node.parent

        # Otherwise it's already definition
        return node

    def _is_private_element(
        self,
        element_def: Node,
        element_info: ElementInfo,
        profile: ElementProfile,
    ) -> bool:
        """
        Check if element is private.

        Args:
            element_def: Definition node of element
            element_info: Element information
            profile: Element profile

        Returns:
            True if element is private and should be removed
        """
        # Use custom visibility logic if specified
        if profile.visibility_check:
            visibility = profile.visibility_check(element_def, self.doc)
            is_public = visibility == "public"
        else:
            is_public = element_info.is_public

        # Use custom export logic if specified
        if profile.export_check:
            is_exported = profile.export_check(element_def, self.doc)
        else:
            is_exported = element_info.is_exported

        # Logic as in current CodeAnalyzer
        return not element_info.in_public_api
