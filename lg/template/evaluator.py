"""
Вычислитель условий для движка шаблонизации LG V2.

Интерпретирует условные выражения в шаблонах с поддержкой тегов,
наборов тегов, режимов и логических операций.
"""

from __future__ import annotations

from typing import Set, Dict

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
    
    def get_active_tags(self) -> Set[str]:
        """Возвращает множество активных тегов."""
        return self.condition_context.active_tags
    
    def get_tagsets(self) -> Dict[str, Set[str]]:
        """Возвращает карту наборов тегов."""
        return self.condition_context.tagsets
    
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


class TemplateEvaluationError(Exception):
    """
    Ошибка вычисления условий в шаблоне.
    
    Расширяет базовую EvaluationError информацией о позиции в шаблоне.
    """
    
    def __init__(self, message: str, condition_text: str, line: int = 0, column: int = 0):
        super().__init__(f"{message} in condition '{condition_text}' at {line}:{column}")
        self.condition_text = condition_text
        self.line = line
        self.column = column


def create_template_evaluator(
    active_tags: Set[str],
    active_modes: Dict[str, str],
    tagsets: Dict[str, Set[str]],
    origin: str = "self"
) -> TemplateConditionEvaluator:
    """
    Удобная функция для создания оценщика условий шаблона.
    
    Args:
        active_tags: Множество активных тегов
        active_modes: Словарь активных режимов {modeset -> mode}
        tagsets: Карта наборов тегов {set_name -> {tag_names}}
        origin: Origin для скоупа ("self" для local, путь для parent)
        
    Returns:
        Настроенный оценщик условий шаблона
    """
    condition_context = ConditionContext(
        active_tags=active_tags,
        tagsets=tagsets,
        origin=origin,
    )
    
    return TemplateConditionEvaluator(condition_context)


def evaluate_simple_condition(
    condition_text: str,
    active_tags: Set[str],
    tagsets: Dict[str, Set[str]] | None = None
) -> bool:
    """
    Простая функция для быстрой оценки условия.
    
    Полезна для тестирования и простых случаев использования.
    
    Args:
        condition_text: Текст условия для оценки
        active_tags: Множество активных тегов
        tagsets: Опциональная карта наборов тегов
        
    Returns:
        Результат вычисления условия
        
    Raises:
        ValueError: При ошибке парсинга
        EvaluationError: При ошибке вычисления
    """
    tagsets = tagsets or {}
    
    evaluator = create_template_evaluator(
        active_tags=active_tags,
        active_modes={},
        tagsets=tagsets
    )
    
    return evaluator.evaluate_condition_text(condition_text)