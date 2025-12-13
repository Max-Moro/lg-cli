"""
Base interface for literal processing components.

Defines the contract that all literal processors must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..patterns import LiteralProfile, TrimResult
from ....tree_sitter_support import TreeSitterDocument, Node


class LiteralProcessor(ABC):
    """
    Abstract base class for all literal processing components.

    All literal processors must implement:
    - can_handle(): Check if component is applicable to a pattern
    - process(): Process the literal and return optimization result
    """

    @abstractmethod
    def can_handle(self, profile: LiteralProfile, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Check if this component can handle the given literal pattern.

        Args:
            profile: Literal profile (StringProfile, SequenceProfile, etc.)
            node: Tree-sitter node representing the literal
            doc: Tree-sitter document

        Returns:
            True if this component should handle the literal
        """
        pass

    @abstractmethod
    def process(
        self,
        node: Node,
        doc: TreeSitterDocument,
        source_text: str,
        profile: LiteralProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """
        Process the literal and return optimization result.

        Args:
            node: Tree-sitter node representing the literal
            doc: Tree-sitter document
            source_text: Full source text
            profile: Literal profile that matched this node
            token_budget: Token budget for optimization

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        pass
