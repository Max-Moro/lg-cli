"""
Base class for language-specific trivial file detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...context import LightweightContext


class TrivialFileAnalyzer(ABC):
    """
    Base class for language-specific trivial file detection.

    Subclasses implement language-specific patterns and heuristics
    to determine if a file should be completely skipped from listings.
    """

    @abstractmethod
    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        """
        Determine if file is trivial and should be skipped.

        Args:
            ctx: Lightweight context with file info and raw text
            adapter: Language adapter (for document creation)

        Returns:
            True if file should be skipped entirely
        """
        pass
