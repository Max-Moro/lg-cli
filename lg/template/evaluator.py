"""
Вычислитель условий для движка шаблонизации.

Интерпретирует условные выражения в шаблонах с поддержкой тегов,
наборов тегов, режимов и логических операций.
"""

from __future__ import annotations

from ..conditions.evaluator import ConditionEvaluator, EvaluationError
from ..conditions.model import Condition
from ..run_context import ConditionContext


class TemplateConditionEvaluator:
    """
    Оценщик условий для шаблонов.

    Расширяет базовый ConditionEvaluator специфичной для шаблонов
    логикой и интеграцией с контекстом рендеринга.
    """

    def __init__(self, condition_context: ConditionContext):
        """
        Инициализирует оценщик с контекстом условий.

        Args:
            condition_context: Контекст с активными тегами, режимами и наборами тегов
        """
        self.condition_context = condition_context
        self.base_evaluator = ConditionEvaluator(condition_context)

    def evaluate(self, condition: Condition) -> bool:
        """
        Вычисляет условие в контексте шаблона.

        Args:
            condition: AST условия для вычисления

        Returns:
            Результат вычисления условия

        Raises:
            EvaluationError: При ошибке вычисления условия
        """
        try:
            return self.base_evaluator.evaluate(condition)
        except EvaluationError:
            # Передаем ошибки дальше с дополнительным контекстом если нужно
            raise

    def evaluate_condition_text(self, condition_text: str) -> bool:
        """
        Вычисляет условие из текстового представления.

        Args:
            condition_text: Текстовое представление условия

        Returns:
            Результат вычисления условия

        Raises:
            ValueError: При ошибке парсинга условия
            EvaluationError: При ошибке вычисления условия
        """
        from ..conditions.parser import ConditionParser

        parser = ConditionParser()
        condition_ast = parser.parse(condition_text)

        return self.evaluate(condition_ast)

    def update_context(self, condition_context: ConditionContext) -> None:
        """
        Обновляет контекст условий.

        Используется при изменении активных тегов или режимов
        внутри блоков {% mode %}.

        Args:
            condition_context: Новый контекст условий
        """
        self.condition_context = condition_context
        self.base_evaluator = ConditionEvaluator(condition_context)

    def is_tag_active(self, tag: str) -> bool:
        """Проверяет, активен ли указанный тег."""
        return self.condition_context.is_tag_active(tag)

    def is_tagset_condition_met(self, set_name: str, tag_name: str) -> bool:
        """
        Проверяет условие набора тегов.

        Args:
            set_name: Имя набора тегов
            tag_name: Имя тега в наборе

        Returns:
            True если условие выполняется
        """
        return self.condition_context.is_tagset_condition_met(set_name, tag_name)