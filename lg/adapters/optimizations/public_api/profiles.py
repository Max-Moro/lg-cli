"""
Element profiles for declarative public API element collection.
Replaces manual _collect_* methods with profile-based system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from ...tree_sitter_support import Node, TreeSitterDocument


@dataclass
class ElementProfile:
    """
    Declarative description of element type for public API filtering.

    Profile describes:
    - How to find elements (query)
    - How to identify them (additional_check)
    - How to determine privacy (visibility_check)
    - How to name them in placeholders (name)
    """

    name: str
    """
    Profile name for metrics and placeholders, e.g., "class", "trait", "case_class".

    Used for:
    - Metrics: {language}.removed.{name}
    - Placeholder: "... {name} omitted ..."
    - Profile inheritance (parent_profile)
    """

    query: str
    """
    Tree-sitter query for finding elements of this type.

    IMPORTANT: Must be single-pattern (no union patterns) to avoid duplicates.
    Capture name must always be @element.

    Examples:
        "(class_definition name: (identifier) @element)"
        "(trait_definition name: (identifier) @element)"
        "(function_declaration name: (identifier) @element)"
    """

    parent_profile: Optional[str] = None
    """
    Name of parent profile for inheritance.

    When inheriting:
    - query is taken from parent (if not overridden)
    - additional_check is combined (parent_check AND child_check)

    Example:
        case_class_profile.parent_profile = "class"
    """

    additional_check: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Additional check that node is of this profile type.

    Used when query cannot precisely filter elements.

    Examples:
        - Distinguish case class from class: lambda node, doc: "case" in doc.get_node_text(node)[:50]
        - Distinguish private typedef struct: lambda node, doc: "static" not in doc.get_node_text(node)

    Signature: (node: Node, doc: TreeSitterDocument) -> bool
    Returns True if this is element of this profile.
    """

    visibility_check: Optional[Callable[[Node, TreeSitterDocument], str]] = None
    """
    Custom logic for determining element visibility.

    Used for languages with non-standard visibility logic:
    - Go: by case of first letter (uppercase = public)
    - JavaScript: by prefix _ or # (convention-based)
    - Python: by prefix _ or __ (convention-based)

    If not specified, uses standard logic via CodeAnalyzer.determine_visibility().

    Signature: (node: Node, doc: TreeSitterDocument) -> str
    Returns: "public", "private", or "protected"
    """

    export_check: Optional[Callable[[Node, TreeSitterDocument], bool]] = None
    """
    Custom logic for determining element export.

    If not specified, uses CodeAnalyzer.determine_export_status().

    Signature: (node: Node, doc: TreeSitterDocument) -> bool
    Returns True if element is exported.
    """

    uses_visibility_for_public_api: bool = True
    """
    Whether this element type uses visibility (public/private/protected) for public API determination.

    - True (default): Element is in public API if it's public (visibility-based)
    - False: Element is in public API if it's exported (export-based)

    Most languages use visibility for most element types (classes, methods, fields).
    Only top-level declarations in some languages use export semantics.

    Examples:
    - Java fields: uses_visibility_for_public_api=True (public/private modifier)
    - Java top-level variables: uses_visibility_for_public_api=True (public/private modifier)
    - TypeScript top-level functions: uses_visibility_for_public_api=False (export keyword)
    - Go everything: uses_visibility_for_public_api=True (naming convention IS visibility)
    """


@dataclass
class LanguageElementProfiles:
    """Collection of element profiles for a specific language."""

    language: str
    """Language name: "scala", "java", "rust", ..."""

    profiles: List[ElementProfile]
    """List of element profiles for this language."""

    def resolve_inheritance(self) -> List[ElementProfile]:
        """
        Resolve profile inheritance.

        Creates flat list of profiles where parent_profile is replaced with actual values.

        Returns:
            List of resolved profiles

        Raises:
            ValueError: If parent profile is not found
        """
        # Build map: name -> profile
        profile_map = {p.name: p for p in self.profiles}

        resolved = []
        for profile in self.profiles:
            if profile.parent_profile:
                parent = profile_map.get(profile.parent_profile)
                if not parent:
                    raise ValueError(f"Unknown parent profile: {profile.parent_profile}")

                # Inherit fields from parent
                # Note: uses_visibility_for_public_api is taken from child if explicitly set, else from parent
                resolved_profile = ElementProfile(
                    name=profile.name,
                    query=profile.query or parent.query,
                    parent_profile=None,  # remove inheritance
                    additional_check=self._combine_checks(
                        parent.additional_check, profile.additional_check
                    ),
                    visibility_check=profile.visibility_check or parent.visibility_check,
                    export_check=profile.export_check or parent.export_check,
                    uses_visibility_for_public_api=profile.uses_visibility_for_public_api,
                )
                resolved.append(resolved_profile)
            else:
                resolved.append(profile)

        return resolved

    @staticmethod
    def _combine_checks(
        parent_check: Optional[Callable],
        child_check: Optional[Callable],
    ) -> Optional[Callable]:
        """
        Combine parent and child additional_check via AND.

        Args:
            parent_check: Parent additional_check function
            child_check: Child additional_check function

        Returns:
            Combined check function or None if both are None
        """
        if not parent_check:
            return child_check
        if not child_check:
            return parent_check

        return lambda node, doc: parent_check(node, doc) and child_check(node, doc)
