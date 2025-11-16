"""
Condition evaluator for template engine.

Interprets conditional expressions in templates with support for tags,
tag sets, modes, and logical operations.
"""

from __future__ import annotations

from ..conditions.evaluator import ConditionEvaluator, EvaluationError
from ..conditions.model import Condition
from ..run_context import ConditionContext


class TemplateConditionEvaluator:
    """
    Condition evaluator for templates.

    Extends base ConditionEvaluator with template-specific
    logic and integration with rendering context.
    """

    def __init__(self, condition_context: ConditionContext):
        """
        Initializes evaluator with condition context.

        Args:
            condition_context: Context with active tags, modes, and tag sets
        """
        self.condition_context = condition_context
        self.base_evaluator = ConditionEvaluator(condition_context)

    def evaluate(self, condition: Condition) -> bool:
        """
        Evaluates condition in template context.

        Args:
            condition: AST of condition to evaluate

        Returns:
            Result of condition evaluation

        Raises:
            EvaluationError: If error during condition evaluation
        """
        try:
            return self.base_evaluator.evaluate(condition)
        except EvaluationError:
            # Pass errors further with additional context if needed
            raise

    def evaluate_condition_text(self, condition_text: str) -> bool:
        """
        Evaluates condition from text representation.

        Args:
            condition_text: Text representation of condition

        Returns:
            Result of condition evaluation

        Raises:
            ValueError: If error parsing condition
            EvaluationError: If error during condition evaluation
        """
        from ..conditions.parser import ConditionParser

        parser = ConditionParser()
        condition_ast = parser.parse(condition_text)

        return self.evaluate(condition_ast)

    def update_context(self, condition_context: ConditionContext) -> None:
        """
        Updates condition context.

        Used when active tags or modes change
        inside {% mode %} blocks.

        Args:
            condition_context: New condition context
        """
        self.condition_context = condition_context
        self.base_evaluator = ConditionEvaluator(condition_context)