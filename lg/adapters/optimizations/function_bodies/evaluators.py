"""
Policy evaluators for function body optimization.
Each evaluator handles a specific aspect of function body processing.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from .decision import FunctionBodyDecision
from ...code_model import FunctionBodyPolicy
from ...shared import CodeElement

logger = logging.getLogger(__name__)


class ExceptPatternEvaluator:
    """Evaluates except_patterns for forced body preservation."""

    def __init__(self, patterns: List[str]):
        self.patterns = patterns

    def evaluate(self, element: CodeElement) -> Optional[FunctionBodyDecision]:
        """
        Check if function name matches any except pattern.

        Args:
            element: CodeElement with function name

        Returns:
            Decision to keep if pattern matches, None otherwise
        """
        if not self.patterns or not element.name:
            return None

        for pattern in self.patterns:
            try:
                if re.search(pattern, element.name):
                    return FunctionBodyDecision(action="keep")
            except re.error as e:
                logger.warning("Invalid regex pattern in except_patterns '%s': %s", pattern, e)
                continue

        return None


class KeepAnnotatedEvaluator:
    """Evaluates keep_annotated for forced body preservation."""

    def __init__(self, patterns: List[str]):
        self.patterns = patterns

    def evaluate(self, element: CodeElement) -> Optional[FunctionBodyDecision]:
        """
        Check if function has any preservation annotations/decorators.

        Args:
            element: CodeElement with decorators

        Returns:
            Decision to keep if annotation matches, None otherwise
        """
        if not self.patterns or not element.decorators:
            return None

        for decorator in element.decorators:
            decorator_text = decorator.text.decode("utf-8") if isinstance(decorator.text, bytes) else str(decorator.text)
            for pattern in self.patterns:
                try:
                    if re.search(pattern, decorator_text):
                        return FunctionBodyDecision(action="keep")
                except re.error as e:
                    logger.warning("Invalid regex pattern in keep_annotated '%s': %s", pattern, e)
                    continue

        return None


class BasePolicyEvaluator:
    """Evaluates base function body policy (keep_all, strip_all, keep_public)."""

    def __init__(self, policy: FunctionBodyPolicy):
        self.policy = policy

    def evaluate(self, element: CodeElement) -> FunctionBodyDecision:
        """
        Apply base function body policy.

        Args:
            element: CodeElement with public API status

        Returns:
            Decision based on policy (always returns a decision)
        """
        if self.policy == "keep_all":
            return FunctionBodyDecision(action="keep")

        elif self.policy == "strip_all":
            return FunctionBodyDecision(action="strip")

        elif self.policy == "keep_public":
            if element.is_public:
                return FunctionBodyDecision(action="keep")
            else:
                return FunctionBodyDecision(action="strip")

        # Fallback (should never happen with valid policy)
        return FunctionBodyDecision(action="keep")


__all__ = [
    "ExceptPatternEvaluator",
    "KeepAnnotatedEvaluator",
    "BasePolicyEvaluator",
]
