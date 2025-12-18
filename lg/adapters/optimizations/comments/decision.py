"""
Decision model for comment optimization.
Provides normalized representation of comment processing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Protocol

from .analyzer import CommentAnalyzer
from ...context import ProcessingContext


@dataclass
class CommentDecision:
    """Normalized decision about comment processing."""
    action: Literal["keep", "remove", "transform"]
    replacement: Optional[str] = None  # None = use placeholder


class PolicyEvaluator(Protocol):
    """Protocol for comment policy evaluators."""

    def evaluate(
        self,
        text: str,
        is_docstring: bool,
        context: ProcessingContext,
        analyzer: CommentAnalyzer
    ) -> Optional[CommentDecision]:
        """
        Evaluate comment and return decision.

        Args:
            text: Comment text content
            is_docstring: Whether this is a documentation comment
            context: Processing context
            analyzer: Language-specific comment analyzer

        Returns:
            CommentDecision if this evaluator applies, None otherwise
        """
        ...


__all__ = ["CommentDecision", "PolicyEvaluator"]
