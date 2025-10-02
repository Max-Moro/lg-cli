"""
Внутренние обработчики для модульного шаблонизатора.

Предоставляет типизированный интерфейс для взаимодействия плагинов
с ядром шаблонизатора, избегая загрязнения внешних контрактов.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from .nodes import TemplateNode, TemplateAST
from ..template.context import TemplateContext
from ..types import SectionRef


@runtime_checkable
class TemplateProcessorHandlers(Protocol):
    """
    Протокол для внутренних обработчиков шаблонизатора.
    
    Определяет типизированный интерфейс для вызова функций ядра
    из плагинов без нарушения инкапсуляции.
    """
    
    def process_ast_node(self, node: TemplateNode, template_ctx: TemplateContext) -> str:
        """
        Обрабатывает один узел AST.
        
        Args:
            node: Узел для обработки
            template_ctx: Контекст шаблона
            
        Returns:
            Отрендеренное содержимое узла
        """
        ...
    
    def process_section_ref(self, section_ref: SectionRef, template_ctx: TemplateContext) -> str:
        """
        Обрабатывает ссылку на секцию.
        
        Args:
            section_ref: Ссылка на секцию для обработки
            template_ctx: Контекст шаблона
            
        Returns:
            Отрендеренное содержимое секции
        """
        ...
    
    def parse_and_process_template(self, template_text: str, template_ctx: TemplateContext) -> str:
        """
        Парсит и обрабатывает текст шаблона.
        
        Используется для обработки включаемых шаблонов.
        
        Args:
            template_text: Текст для парсинга и обработки
            template_ctx: Контекст шаблона
            
        Returns:
            Отрендеренный результат
        """
        ...


class DefaultTemplateProcessorHandlers:
    """
    Реализация внутренних обработчиков шаблонизатора по умолчанию.
    
    Связывает плагины с основной логикой процессора шаблонов.
    """
    
    def __init__(self):
        """Инициализирует обработчики."""
        self._ast_processor: Callable[[TemplateNode, TemplateContext], str] | None = None
        self._section_processor: Callable[[SectionRef, TemplateContext], str] | None = None
        self._template_parser: Callable[[str, TemplateContext], str] | None = None
    
    def set_ast_processor(self, processor: Callable[[TemplateNode, TemplateContext], str]) -> None:
        """Устанавливает процессор узлов AST."""
        self._ast_processor = processor
    
    def set_section_processor(self, processor: Callable[[SectionRef, TemplateContext], str]) -> None:
        """Устанавливает процессор секций."""
        self._section_processor = processor
    
    def set_template_parser(self, parser: Callable[[str, TemplateContext], str]) -> None:
        """Устанавливает парсер шаблонов."""
        self._template_parser = parser
    
    def process_ast_node(self, node: TemplateNode, template_ctx: TemplateContext) -> str:
        """Обрабатывает один узел AST."""
        if self._ast_processor is None:
            raise RuntimeError("AST processor not set")
        return self._ast_processor(node, template_ctx)
    
    def process_section_ref(self, section_ref: SectionRef, template_ctx: TemplateContext) -> str:
        """Обрабатывает ссылку на секцию."""
        if self._section_processor is None:
            raise RuntimeError("Section processor not set")
        return self._section_processor(section_ref, template_ctx)
    
    def parse_and_process_template(self, template_text: str, template_ctx: TemplateContext) -> str:
        """Парсит и обрабатывает текст шаблона."""
        if self._template_parser is None:
            raise RuntimeError("Template parser not set")
        return self._template_parser(template_text, template_ctx)


__all__ = [
    "TemplateProcessorHandlers",
    "DefaultTemplateProcessorHandlers"
]