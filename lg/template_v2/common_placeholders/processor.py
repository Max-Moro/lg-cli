"""
Обработчики узлов для базовых плейсхолдеров секций и шаблонов.

Реализует логику рендеринга SectionNode и IncludeNode,
вызывая соответствующие обработчики из основного движка.
"""

from __future__ import annotations

from typing import List

from .nodes import SectionNode, IncludeNode
from ..base import ProcessorRule
from ..nodes import TemplateNode


def _process_section_node_impl(node: SectionNode, handlers) -> str:
    """
    Обрабатывает узел секции.
    
    Использует типизированные обработчики ядра шаблонизатора
    для получения отрендеренного содержимого секции.
    
    Args:
        node: Узел секции для обработки
        handlers: Типизированные обработчики ядра
        
    Returns:
        Отрендеренное содержимое секции
        
    Raises:
        RuntimeError: Если секция не найдена
    """
    
    # Используем резолвленную ссылку если есть, иначе используем имя узла
    if node.resolved_ref is not None:
        section_ref = node.resolved_ref
    else:
        # Создаем базовую ссылку на секцию - процессор должен иметь свой контекст
        raise RuntimeError(f"Section node '{node.section_name}' not resolved - resolver should set resolved_ref")
    
    try:
        # Вызываем типизированный обработчик секций (без передачи контекста)
        return handlers.process_section_ref(section_ref)
    except Exception as e:
        raise RuntimeError(f"Failed to process section '{node.section_name}': {e}")


def _process_include_node_impl(node: IncludeNode, handlers) -> str:
    """
    Обрабатывает узел включения шаблона/контекста.
    
    Использует типизированные обработчики ядра для рендеринга
    включенного AST.
    
    Args:
        node: Узел включения для обработки
        handlers: Типизированные обработчики ядра
        
    Returns:
        Отрендеренное содержимое включения
        
    Raises:
        RuntimeError: Если включение не загружено или произошла ошибка рендеринга
    """
    if node.children is None:
        raise RuntimeError(f"Include '{node.canon_key()}' not resolved (children is None)")
    
    # Рендерим включенный AST через типизированные обработчики
    result_parts = []
    
    for child_node in node.children:
        rendered = handlers.process_ast_node(child_node)
        if rendered:
            result_parts.append(rendered)
    
    return "".join(result_parts)


class CommonPlaceholdersProcessor:
    """
    Процессор узлов для базовых плейсхолдеров.
    
    Содержит обработчики ядра и предоставляет методы для
    обработки секционных узлов и узлов включений.
    """
    
    def __init__(self, handlers):
        """
        Инициализирует процессор.
        
        Args:
            handlers: Типизированные обработчики ядра
        """
        # Внутренний импорт для избежания циклических зависимостей
        from ..handlers import TemplateProcessorHandlers
        
        self.handlers: TemplateProcessorHandlers = handlers
    
    def process_section_node(self, node: TemplateNode) -> str:
        """Обрабатывает узел секции."""
        if not isinstance(node, SectionNode):
            raise RuntimeError(f"Expected SectionNode, got {type(node)}")
        return _process_section_node_impl(node, self.handlers)

    def process_include_node(self, node: TemplateNode) -> str:
        """Обрабатывает узел включения.""" 
        if not isinstance(node, IncludeNode):
            raise RuntimeError(f"Expected IncludeNode, got {type(node)}")
        return _process_include_node_impl(node, self.handlers)


def get_processor_rules(processor: CommonPlaceholdersProcessor) -> List[ProcessorRule]:
    """
    Возвращает правила обработки для узлов базовых плейсхолдеров.
    
    Args:
        processor: Экземпляр процессора с настроенными обработчиками
        
    Returns:
        Список правил обработки узлов
    """
    return [
        ProcessorRule(
            node_type=SectionNode,
            processor_func=processor.process_section_node,
            priority=100
        ),
        ProcessorRule(
            node_type=IncludeNode, 
            processor_func=processor.process_include_node,
            priority=100
        )
    ]


__all__ = ["CommonPlaceholdersProcessor", "get_processor_rules"]