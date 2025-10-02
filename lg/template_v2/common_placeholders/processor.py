"""
Обработчики узлов для базовых плейсхолдеров секций и шаблонов.

Реализует логику рендеринга SectionNode и IncludeNode,
вызывая соответствующие обработчики из основного движка.
"""

from __future__ import annotations

from typing import List, Any, TYPE_CHECKING

from ..base import ProcessorRule
from ..nodes import TemplateNode
from .nodes import SectionNode, IncludeNode
from ...template.context import TemplateContext
from ...types import SectionRef

if TYPE_CHECKING:
    from ..handlers import TemplateProcessorHandlers


def _process_section_node_impl(node: SectionNode, template_ctx: TemplateContext, handlers) -> str:
    """
    Обрабатывает узел секции.
    
    Использует типизированные обработчики ядра шаблонизатора
    для получения отрендеренного содержимого секции.
    
    Args:
        node: Узел секции для обработки
        template_ctx: Контекст шаблона
        handlers: Типизированные обработчики ядра
        
    Returns:
        Отрендеренное содержимое секции
        
    Raises:
        RuntimeError: Если секция не найдена
    """
    
    # Используем резолвленную ссылку если есть, иначе создаем простую
    if node.resolved_ref is not None:
        section_ref = node.resolved_ref
    else:
        # Создаем локальную ссылку на секцию
        section_ref = SectionRef(
            name=node.section_name,
            scope_rel="",
            scope_dir=template_ctx.run_ctx.root
        )
    
    try:
        # Вызываем типизированный обработчик секций
        return handlers.process_section_ref(section_ref, template_ctx)
    except Exception as e:
        raise RuntimeError(f"Failed to process section '{node.section_name}': {e}")


def _process_include_node_impl(node: IncludeNode, template_ctx: TemplateContext, handlers) -> str:
    """
    Обрабатывает узел включения шаблона/контекста.
    
    Использует типизированные обработчики ядра для рендеринга
    включенного AST в контексте текущего шаблона.
    
    Args:
        node: Узел включения для обработки
        template_ctx: Контекст шаблона
        handlers: Типизированные обработчики ядра
        
    Returns:
        Отрендеренное содержимое включения
        
    Raises:
        RuntimeError: Если включение не загружено или произошла ошибка рендеринга
    """
    if node.children is None:
        raise RuntimeError(f"Include '{node.canon_key()}' not resolved (children is None)")
    
    # Входим в скоуп включения для корректной обработки адресных ссылок
    template_ctx.enter_include_scope(node.origin)
    
    try:
        # Рендерим включенный AST через типизированные обработчики
        result_parts = []
        
        for child_node in node.children:
            rendered = handlers.process_ast_node(child_node, template_ctx)
            if rendered:
                result_parts.append(rendered)
        
        return "".join(result_parts)
        
    finally:
        # Выходим из скоупа включения
        template_ctx.exit_include_scope()


class CommonPlaceholdersProcessor:
    """
    Процессор узлов для базовых плейсхолдеров.
    
    Содержит обработчики ядра и предоставляет методы для
    обработки секционных узлов и узлов включений.
    """
    
    def __init__(self, handlers: 'TemplateProcessorHandlers'):
        """
        Инициализирует процессор.
        
        Args:
            handlers: Типизированные обработчики ядра
        """
        self.handlers = handlers
    
    def process_section_node(self, node: TemplateNode, context: Any) -> str:
        """Обрабатывает узел секции."""
        if not isinstance(node, SectionNode):
            raise RuntimeError(f"Expected SectionNode, got {type(node)}")
        return _process_section_node_impl(node, context, self.handlers)

    def process_include_node(self, node: TemplateNode, context: Any) -> str:
        """Обрабатывает узел включения.""" 
        if not isinstance(node, IncludeNode):
            raise RuntimeError(f"Expected IncludeNode, got {type(node)}")
        return _process_include_node_impl(node, context, self.handlers)


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