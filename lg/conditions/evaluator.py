"""
Вычислитель условных выражений.

Проходит по AST условий и вычисляет их значения в контексте активных тегов,
наборов тегов и информации о скоупах.
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
    """Ошибка при вычислении условного выражения."""
    pass


class ConditionEvaluator:
    """
    Вычислитель условных выражений.
    
    Принимает AST условия и контекст выполнения, возвращает булево значение.
    """
    
    def __init__(self, context: ConditionContext):
        """
        Инициализирует вычислитель с контекстом.

        Args:
            context: Контекст с информацией об активных тегах и скоупах
        """
        self.context = context

    def evaluate(self, condition: Condition) -> bool:
        """
        Вычисляет значение условия.

        Args:
            condition: Корневой узел AST условия

        Returns:
            Булево значение результата вычисления

        Raises:
            EvaluationError: При ошибке вычисления (например, неизвестный тип условия)
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
        Вычисляет условие тега: tag:name

        Истинно, если указанный тег активен в контексте.
        """
        return self.context.is_tag_active(condition.name)

    def _evaluate_tagset(self, condition: TagSetCondition) -> bool:
        """
        Вычисляет условие набора тегов: TAGSET:set_name:tag_name

        Правила:
        - Истинно, если ни один тег из набора не активен
        - Истинно, если указанный тег активен
        - Ложно во всех остальных случаях
        """
        return self.context.is_tagset_condition_met(condition.set_name, condition.tag_name)

    def _evaluate_scope(self, condition: ScopeCondition) -> bool:
        """
        Вычисляет условие скоупа: scope:type

        Зависит от текущего контекста выполнения (локальный/родительский скоуп).
        """
        return self.context.is_scope_condition_met(condition.scope_type)

    def _evaluate_task(self, condition: TaskCondition) -> bool:
        """
        Вычисляет условие task.

        Истинно, если задан непустой текст задачи.
        """
        return self.context.is_task_provided()

    def _evaluate_group(self, condition: GroupCondition) -> bool:
        """
        Вычисляет группированное условие: (condition)

        Просто вычисляет вложенное условие.
        """
        return self.evaluate(condition.condition)

    def _evaluate_not(self, condition: NotCondition) -> bool:
        """
        Вычисляет отрицание: NOT condition

        Инвертирует результат вычисления вложенного условия.
        """
        return not self.evaluate(condition.condition)

    def _evaluate_and(self, condition: BinaryCondition) -> bool:
        """
        Вычисляет логическое И: left AND right

        Истинно, если оба операнда истинны.
        Использует короткое вычисление (short-circuit evaluation).
        """
        left_result = self.evaluate(condition.left)
        if not left_result:
            return False  # Короткое вычисление

        return self.evaluate(condition.right)

    def _evaluate_or(self, condition: BinaryCondition) -> bool:
        """
        Вычисляет логическое ИЛИ: left OR right

        Истинно, если хотя бы один операнд истинен.
        Использует короткое вычисление (short-circuit evaluation).
        """
        left_result = self.evaluate(condition.left)
        if left_result:
            return True  # Короткое вычисление

        return self.evaluate(condition.right)


def evaluate_condition_string(condition_str: str, context: ConditionContext) -> bool:
    """
    Удобная функция для вычисления условия из строки.
    
    Args:
        condition_str: Строка условного выражения
        context: Контекст выполнения
        
    Returns:
        Результат вычисления условия
        
    Raises:
        ValueError: При ошибке парсинга
        EvaluationError: При ошибке вычисления
    """
    from .parser import ConditionParser
    
    parser = ConditionParser()
    ast = parser.parse(condition_str)
    
    evaluator = ConditionEvaluator(context)
    return evaluator.evaluate(ast)