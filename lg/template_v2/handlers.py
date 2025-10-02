"""
Внутренние обработчики для модульного шаблонизатора.

Предоставляет типизированный интерфейс для взаимодействия плагинов
с ядром шаблонизатора, избегая загрязнения внешних контрактов.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .nodes import TemplateNode
from ..types import SectionRef


@runtime_checkable
class TemplateProcessorHandlers(Protocol):
    """
    Протокол для внутренних обработчиков шаблонизатора.
    
    Определяет типизированный интерфейс для вызова функций ядра
    из плагинов без нарушения инкапсуляции.
    """
    
    def process_ast_node(self, node: TemplateNode) -> str:
        """
        Обрабатывает один узел AST.
        
        Args:
            node: Узел для обработки
            
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


__all__ = ["TemplateProcessorHandlers"]