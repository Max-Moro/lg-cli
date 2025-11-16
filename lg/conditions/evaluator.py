"""
Evaluator for conditional expressions.

Traverses the AST of conditions and evaluates their values in the context of active tags,
tag sets, and scope information.
"""

from __future__ import annotations

from typing import cast

from .model import (
    Condition,
    ConditionType,
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    TaskCondition,
    GroupCondition,
    NotCondition,
    BinaryCondition,
)

from ..run_context import ConditionContext


class EvaluationError(Exception):
    """Error during evaluation of a conditional expression."""
    pass


class ConditionEvaluator:
    """
    Evaluator for conditional expressions.

    Takes a condition AST and execution context, returns a boolean value.
    """
    
    def __init__(self, context: ConditionContext):
        """
        Initialize the evaluator with a context.

        Args:
            context: Context with information about active tags and scopes
        """
        self.context = context

    def evaluate(self, condition: Condition) -> bool:
        """
        Evaluate the value of a condition.

        Args:
            condition: Root node of the condition AST

        Returns:
            Boolean value of the evaluation result

        Raises:
            EvaluationError: On evaluation error (e.g., unknown condition type)
        """
        condition_type = condition.get_type()

        if condition_type == ConditionType.TAG:
            return self._evaluate_tag(cast(TagCondition, condition))
        elif condition_type == ConditionType.TAGSET:
            return self._evaluate_tagset(cast(TagSetCondition, condition))
        elif condition_type == ConditionType.SCOPE:
            return self._evaluate_scope(cast(ScopeCondition, condition))
        elif condition_type == ConditionType.TASK:
            return self._evaluate_task(cast(TaskCondition, condition))
        elif condition_type == ConditionType.GROUP:
            return self._evaluate_group(cast(GroupCondition, condition))
        elif condition_type == ConditionType.NOT:
            return self._evaluate_not(cast(NotCondition, condition))
        elif condition_type == ConditionType.AND:
            return self._evaluate_and(cast(BinaryCondition, condition))
        elif condition_type == ConditionType.OR:
            return self._evaluate_or(cast(BinaryCondition, condition))
        else:
            raise EvaluationError(f"Unknown condition type: {condition_type}")

    def _evaluate_tag(self, condition: TagCondition) -> bool:
        """
        Evaluate a tag condition: tag:name

        True if the specified tag is active in the context.
        """
        return self.context.is_tag_active(condition.name)

    def _evaluate_tagset(self, condition: TagSetCondition) -> bool:
        """
        Evaluate a tag set condition: TAGSET:set_name:tag_name

        Rules:
        - True if no tags in the set are active
        - True if the specified tag is active
        - False in all other cases
        """
        return self.context.is_tagset_condition_met(condition.set_name, condition.tag_name)

    def _evaluate_scope(self, condition: ScopeCondition) -> bool:
        """
        Evaluate a scope condition: scope:type

        Depends on the current execution context (local/parent scope).
        """
        return self.context.is_scope_condition_met(condition.scope_type)

    def _evaluate_task(self, _condition: TaskCondition) -> bool:
        """
        Evaluate a task condition.

        True if a non-empty task text is provided.
        """
        return self.context.is_task_provided()

    def _evaluate_group(self, condition: GroupCondition) -> bool:
        """
        Evaluate a grouped condition: (condition)

        Simply evaluates the nested condition.
        """
        return self.evaluate(condition.condition)

    def _evaluate_not(self, condition: NotCondition) -> bool:
        """
        Evaluate a negation: NOT condition

        Inverts the evaluation result of the nested condition.
        """
        return not self.evaluate(condition.condition)

    def _evaluate_and(self, condition: BinaryCondition) -> bool:
        """
        Evaluate a logical AND: left AND right

        True if both operands are true.
        Uses short-circuit evaluation.
        """
        left_result = self.evaluate(condition.left)
        if not left_result:
            return False  # Short-circuit evaluation

        return self.evaluate(condition.right)

    def _evaluate_or(self, condition: BinaryCondition) -> bool:
        """
        Evaluate a logical OR: left OR right

        True if at least one operand is true.
        Uses short-circuit evaluation.
        """
        left_result = self.evaluate(condition.left)
        if left_result:
            return True  # Short-circuit evaluation

        return self.evaluate(condition.right)


def evaluate_condition_string(condition_str: str, context: ConditionContext) -> bool:
    """
    Convenience function to evaluate a condition from a string.

    Args:
        condition_str: Condition expression string
        context: Execution context

    Returns:
        Result of the condition evaluation

    Raises:
        ValueError: On parsing error
        EvaluationError: On evaluation error
    """
    from .parser import ConditionParser
    
    parser = ConditionParser()
    ast = parser.parse(condition_str)
    
    evaluator = ConditionEvaluator(context)
    return evaluator.evaluate(ast)