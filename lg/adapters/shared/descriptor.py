"""
Language code descriptor.
Central declaration of all code element profiles for a language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument
from .profiles import ElementProfile, InheritMode


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

    compute_element_range: Optional[Callable[[Node, str, TreeSitterDocument], Optional[Tuple[int, int]]]] = None
    """
    Compute adjusted byte range for element.

    Used to include trailing punctuation (semicolons, commas) or exclude
    leading noise from element boundaries.

    Args:
        node: Element node
        element_type: Type of element ("field", "variable", etc.)
        doc: Tree-sitter document

    Returns:
        Tuple (start_byte, end_byte) if range should be adjusted, None otherwise.

    Signature: (node: Node, element_type: str, doc: TreeSitterDocument) -> Optional[Tuple[int, int]]
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

        Creates flat list where inherit_previous is replaced with inherited values.
        """
        resolved = []

        for i, profile in enumerate(self.profiles):
            if profile.inherit_previous != InheritMode.NONE:
                if i == 0:
                    raise ValueError(f"Profile '{profile.name}' has inherit_previous={profile.inherit_previous} but is first in list")

                # Get parent from resolved list (already has inherited values)
                parent = resolved[i - 1]

                # Determine additional_check based on inheritance mode
                if profile.additional_check is not None:
                    # Explicit check specified - use it
                    resolved_check = profile.additional_check
                elif profile.inherit_previous == InheritMode.NEGATE_CHECK:
                    # Negate parent's check
                    if parent.additional_check is not None:
                        parent_check = parent.additional_check
                        resolved_check = lambda node, doc, pc=parent_check: not pc(node, doc)
                    else:
                        resolved_check = None
                else:
                    # INHERIT mode - use parent's check as-is
                    resolved_check = parent.additional_check

                # Inherit fields from previous profile
                # For has_body: inherit from parent only if current is False (default)
                # This allows explicit has_body=True to override, but inherits True from parent
                resolved_profile = ElementProfile(
                    name=profile.name if profile.name else parent.name,
                    query=profile.query if profile.query else parent.query,
                    is_public=profile.is_public if profile.is_public is not None else parent.is_public,
                    additional_check=resolved_check,
                    has_body=profile.has_body or parent.has_body,  # Inherit True from parent
                    body_query=profile.body_query if profile.body_query is not None else parent.body_query,
                    docstring_extractor=profile.docstring_extractor if profile.docstring_extractor is not None else parent.docstring_extractor,
                    body_resolver=profile.body_resolver if profile.body_resolver is not None else parent.body_resolver,
                    body_range_computer=profile.body_range_computer if profile.body_range_computer is not None else parent.body_range_computer,
                    inherit_previous=InheritMode.NONE,  # Remove inheritance marker
                )
                resolved.append(resolved_profile)
            else:
                resolved.append(profile)

        return resolved


__all__ = ["LanguageCodeDescriptor"]
