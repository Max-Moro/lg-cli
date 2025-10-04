"""
Внутренние обработчики для модульного шаблонизатора.

Предоставляет типизированный интерфейс для взаимодействия плагинов
с ядром шаблонизатора, избегая загрязнения внешних контрактов.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .nodes import TemplateNode
from .types import ProcessingContext
from ..types import SectionRef


@runtime_checkable
class TemplateProcessorHandlers(Protocol):
    """
    Протокол для внутренних обработчиков шаблонизатора.
    
    Определяет типизированный интерфейс для вызова функций ядра
    из плагинов без нарушения инкапсуляции.
    """
    
    def process_ast_node(self, context: ProcessingContext) -> str:
        """
        Обрабатывает один узел AST с контекстом.
        
        Args:
            context: Контекст обработки (ProcessingContext)
            
        Returns:
            Отрендеренное содержимое узла
        """
        ...
    
    def process_section_ref(self, section_ref: SectionRef) -> str:
        """
        Обрабатывает ссылку на секцию.
        
        Args:
            section_ref: Ссылка на секцию для обработки
            
        Returns:
            Отрендеренное содержимое секции
        """
        ...
    
    def parse_next_node(self, context) -> TemplateNode | None:
        """
        Парсит следующий узел из контекста парсинга.
        
        Применяет все зарегистрированные правила парсинга для текущей позиции.
        Используется для рекурсивного парсинга вложенных структур.
        
        Args:
            context: Контекст парсинга (ParsingContext)
            
        Returns:
            Узел AST или None если ни одно правило не сработало
        """
        ...
    
    def resolve_ast(self, ast, context: str = "") -> list:
        """
        Резолвит AST рекурсивно через все зарегистрированные резолверы.
        
        Применяет резолверы всех плагинов, обрабатывая вложенные узлы.
        Используется плагинами для делегирования рекурсивного резолвинга ядру.
        
        Args:
            ast: AST для резолвинга
            context: Контекст для диагностики
            
        Returns:
            Резолвленный AST
        """
        ...


__all__ = ["TemplateProcessorHandlers"]