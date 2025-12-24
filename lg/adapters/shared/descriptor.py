"""
Language code descriptor.
Central declaration of all code element profiles for a language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument
from .profiles import ElementProfile


@dataclass
class LanguageCodeDescriptor:
    """
    Declarative description of code elements for a language.

    Analogous to LanguageLiteralDescriptor but for code structure elements.
    Each language adapter provides one instance of this class.
    """

    language: str
    """Language name: "python", "typescript", "java", etc."""

    profiles: List[ElementProfile]
    """All element profiles for this language."""

    # --- Language-specific utilities ---

    decorator_types: Set[str] = field(default_factory=set)
    """
    Node types for decorators/annotations.
    Examples: {"decorator"} for Python, {"annotation"} for Java.
    Used to find decorators attached to elements.
    """

    comment_types: Set[str] = field(default_factory=set)
    """
    Node types for comments.
    Examples: {"comment"} for Python, {"comment", "line_comment", "block_comment"} for Java.
    Used to identify whitespace/comment nodes.
    """

    name_extractor: Optional[Callable[[Node, TreeSitterDocument], Optional[str]]] = None
    """
    Language-specific name extraction logic.

    If None, collector uses default heuristic:
    - Look for child with type "identifier" or "type_identifier"
    - Try node.child_by_field_name("name")

    Signature: (node: Node, doc: TreeSitterDocument) -> Optional[str]
    """

    extend_element_range: Optional[Callable[[Node, str, TreeSitterDocument], Node]] = None
    """
    Extend element range to include trailing punctuation.

    Used for TypeScript/JavaScript to include trailing semicolons in element range.
    This ensures proper grouping of adjacent elements in placeholder system.

    Args:
        node: Element node
        element_type: Type of element ("field", "variable", etc.)
        doc: Tree-sitter document

    Returns:
        Node with potentially extended range (may be synthetic ExtendedRangeNode)

    Signature: (node: Node, element_type: str, doc: TreeSitterDocument) -> Node
    """

    decorator_finder: Optional[Callable[[Node, TreeSitterDocument, Set[str]], List[Node]]] = None
    """
    Custom decorator/annotation finder for language-specific AST structures.

    Use when language has non-standard decorator placement that default logic can't handle.
    Example: Kotlin places annotations inside 'modifiers' node or nested 'annotated_expression'.

    If None, collector uses standard strategies:
    - Check parent for decorated_definition wrapper
    - Check preceding siblings

    Args:
        node: Element node
        doc: Tree-sitter document
        decorator_types: Set of decorator node types to search for

    Returns:
        List of decorator nodes attached to this element

    Signature: (node: Node, doc: TreeSitterDocument, decorator_types: Set[str]) -> List[Node]
    """

    # --- Resolved profiles cache ---

    _resolved_profiles: Optional[List[ElementProfile]] = field(default=None, repr=False)

    def get_profiles(self) -> List[ElementProfile]:
        """
        Get resolved profiles with inheritance applied.

        Caches result for efficiency.

        Returns:
            List of profiles with parent references resolved.
        """
        if self._resolved_profiles is None:
            self._resolved_profiles = self._resolve_inheritance()
        return self._resolved_profiles

    def _resolve_inheritance(self) -> List[ElementProfile]:
        """
        Resolve profile inheritance.

        Creates flat list where parent_profile is replaced with inherited values.
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
                resolved_profile = ElementProfile(
                    name=profile.name,
                    query=profile.query or parent.query,
                    is_public=profile.is_public if profile.is_public is not None else parent.is_public,
                    additional_check=self._combine_checks(parent.additional_check, profile.additional_check),
                    has_body=profile.has_body if profile.has_body else parent.has_body,
                    body_query=profile.body_query or parent.body_query,
                    docstring_extractor=profile.docstring_extractor or parent.docstring_extractor,
                    parent_profile=None,  # Remove inheritance marker
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
        """Combine parent and child additional_check via AND."""
        if not parent_check:
            return child_check
        if not child_check:
            return parent_check

        return lambda node, doc: parent_check(node, doc) and child_check(node, doc)


__all__ = ["LanguageCodeDescriptor"]
