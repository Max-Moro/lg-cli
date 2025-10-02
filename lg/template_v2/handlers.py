"""
Внутренние обработчики для модульного шаблонизатора.

Предоставляет типизированный интерфейс для взаимодействия плагинов
с ядром шаблонизатора, избегая загрязнения внешних контрактов.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

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
    
    def parse_and_process_template(self, template_text: str, template_name: str) -> str:
        """
        Парсит и обрабатывает текст шаблона.
        
        Используется для обработки включаемых шаблонов.
        
        Args:
            template_text: Текст для парсинга и обработки
            template_name: Имя шаблона для диагностики (например, "tpl:footer")
            
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
        self._ast_processor: Callable[[TemplateNode], str] | None = None
        self._section_processor: Callable[[SectionRef], str] | None = None
        self._template_parser: Callable[[str, str], str] | None = None
    
    def set_ast_processor(self, processor: Callable[[TemplateNode], str]) -> None:
        """Устанавливает процессор узлов AST."""
        self._ast_processor = processor
    
    def set_section_processor(self, processor: Callable[[SectionRef], str]) -> None:
        """Устанавливает процессор секций."""
        self._section_processor = processor
    
    def set_template_parser(self, parser: Callable[[str, str], str]) -> None:
        """Устанавливает парсер шаблонов (text, template_name) -> str."""
        self._template_parser = parser
    
    def process_ast_node(self, node: TemplateNode) -> str:
        """Обрабатывает один узел AST."""
        if self._ast_processor is None:
            raise RuntimeError("AST processor not set")
        return self._ast_processor(node)
    
    def process_section_ref(self, section_ref: SectionRef) -> str:
        """Обрабатывает ссылку на секцию."""
        if self._section_processor is None:
            raise RuntimeError("Section processor not set")
        return self._section_processor(section_ref)
    
    def parse_and_process_template(self, template_text: str, template_name: str = "") -> str:
        """Парсит и обрабатывает текст шаблона."""
        if self._template_parser is None:
            raise RuntimeError("Template parser not set")
        return self._template_parser(template_text, template_name)


__all__ = [
    "TemplateProcessorHandlers",
    "DefaultTemplateProcessorHandlers"
]