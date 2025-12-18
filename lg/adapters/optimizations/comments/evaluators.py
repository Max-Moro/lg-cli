"""
Concrete policy evaluator implementations for comment optimization.
Each evaluator handles a specific aspect of comment processing.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from .analyzer import CommentAnalyzer
from .decision import CommentDecision, PolicyEvaluator
from ...code_model import CommentPolicy
from ...context import ProcessingContext

logger = logging.getLogger(__name__)


class StripPatternEvaluator(PolicyEvaluator):
    """Evaluates strip_patterns for forced comment removal."""

    def __init__(self, patterns: List[str]):
        """
        Initialize evaluator with strip patterns.

        Args:
            patterns: List of regex patterns for forced removal
        """
        self.patterns = patterns

    def evaluate(
        self,
        text: str,
        is_docstring: bool,
        analyzer: CommentAnalyzer
    ) -> Optional[CommentDecision]:
        """
        Check if comment matches any strip pattern.

        Args:
            text: Comment text content
            is_docstring: Whether this is a documentation comment
            analyzer: Language-specific comment analyzer

        Returns:
            Decision to remove if pattern matches, None otherwise
        """
        for pattern in self.patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return CommentDecision(
                        action="remove",
                        replacement=None  # Use placeholder
                    )
            except re.error as e:
                logger.warning("Invalid regex pattern in strip_patterns '%s': %s", pattern, e)
                continue

        return None  # Not applicable


class KeepAnnotationEvaluator(PolicyEvaluator):
    """Evaluates keep_annotations for forced comment preservation."""

    def __init__(self, patterns: List[str]):
        """
        Initialize evaluator with keep patterns.

        Args:
            patterns: List of regex patterns for preservation
        """
        self.patterns = patterns

    def evaluate(
        self,
        text: str,
        is_docstring: bool,
        analyzer: CommentAnalyzer
    ) -> Optional[CommentDecision]:
        """
        Check if comment matches any keep annotation pattern.

        Args:
            text: Comment text content
            is_docstring: Whether this is a documentation comment
            analyzer: Language-specific comment analyzer

        Returns:
            Decision to keep if pattern matches, None otherwise
        """
        for pattern in self.patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    # Keep, but may need truncation (handled by MaxTokensTransformer)
                    return CommentDecision(
                        action="keep",
                        replacement=text
                    )
            except re.error as e:
                logger.warning("Invalid regex pattern in keep_annotations '%s': %s", pattern, e)
                continue

        return None  # Not applicable


class BasePolicyEvaluator(PolicyEvaluator):
    """Evaluates base comment policy (keep_all, strip_all, keep_doc, keep_first_sentence)."""

    def __init__(self, policy: CommentPolicy):
        """
        Initialize evaluator with base policy.

        Args:
            policy: Base comment policy to apply
        """
        self.policy = policy

    def evaluate(
        self,
        text: str,
        is_docstring: bool,
        analyzer: CommentAnalyzer
    ) -> Optional[CommentDecision]:
        """
        Apply base comment policy.

        Args:
            text: Comment text content
            is_docstring: Whether this is a documentation comment
            analyzer: Language-specific comment analyzer

        Returns:
            Decision based on policy (always returns a decision)
        """
        if self.policy == "keep_all":
            return CommentDecision("keep", replacement=text)

        elif self.policy == "strip_all":
            return CommentDecision("remove", replacement=None)

        elif self.policy == "keep_doc":
            if is_docstring:
                return CommentDecision("keep", replacement=text)
            else:
                return CommentDecision("remove", replacement=None)

        elif self.policy == "keep_first_sentence":
            if is_docstring:
                first_sentence = analyzer.extract_first_sentence(text)
                if first_sentence != text:
                    return CommentDecision("transform", replacement=first_sentence)
                else:
                    return CommentDecision("keep", replacement=text)
            else:
                # Regular comments get removed with placeholder
                return CommentDecision("remove", replacement=None)

        # Should never happen with valid CommentPolicy
        return CommentDecision("keep", replacement=text)


class MaxTokensTransformer:
    """Post-processes decisions to enforce max_tokens constraint."""

    def __init__(self, max_tokens: Optional[int]):
        """
        Initialize transformer with token limit.

        Args:
            max_tokens: Maximum allowed tokens for preserved comments (None = no limit)
        """
        self.max_tokens = max_tokens

    def transform(
        self,
        decision: CommentDecision,
        context: ProcessingContext,
        analyzer: CommentAnalyzer
    ) -> CommentDecision:
        """
        Transform decision if max_tokens constraint is violated.

        Args:
            decision: Original decision from evaluators
            context: Processing context with tokenizer
            analyzer: Language-specific comment analyzer for truncation

        Returns:
            Transformed decision with truncated content if needed
        """
        if self.max_tokens is None:
            return decision

        # Only apply to kept or transformed comments
        if decision.action not in ("keep", "transform"):
            return decision

        text = decision.replacement
        if context.tokenizer.count_text_cached(text) > self.max_tokens:
            truncated = analyzer.truncate_comment(
                text, self.max_tokens, context.tokenizer
            )
            return CommentDecision(
                action="transform",
                replacement=truncated
            )

        return decision


__all__ = [
    "StripPatternEvaluator",
    "KeepAnnotationEvaluator",
    "BasePolicyEvaluator",
    "MaxTokensTransformer",
]
