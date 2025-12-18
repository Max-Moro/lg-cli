"""
Decision model for comment optimization.
Provides normalized representation of comment processing decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Protocol, runtime_checkable

from .analyzer import CommentAnalyzer


@dataclass
class CommentDecision:
    """Normalized decision about comment processing."""
    action: Literal["keep", "remove", "transform"]
    replacement: Optional[str] = None  # None = use placeholder


@runtime_checkable
class PolicyEvaluator(Protocol):
    """Protocol for comment policy evaluators."""

    def evaluate(
        self,
        text: str,
        is_docstring: bool,
        analyzer: CommentAnalyzer
    ) -> Optional[CommentDecision]:
        """
        Evaluate comment and return decision.

        Args:
            text: Comment text content
            is_docstring: Whether this is a documentation comment
            analyzer: Language-specific comment analyzer

        Returns:
            CommentDecision if this evaluator applies, None otherwise
        """
        ...


__all__ = ["CommentDecision", "PolicyEvaluator"]
