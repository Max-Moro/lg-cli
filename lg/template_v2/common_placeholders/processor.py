"""
Обработчики узлов для базовых плейсхолдеров секций и шаблонов.

Реализует логику рендеринга SectionNode и IncludeNode,
вызывая соответствующие обработчики из основного движка.
"""

from __future__ import annotations

from typing import List, Any

from ..base import ProcessorRule
from ..nodes import TemplateNode
from .nodes import SectionNode, IncludeNode
from ...template.context import TemplateContext
from ...types import SectionRef


def _process_section_node_impl(node: SectionNode, template_ctx: TemplateContext) -> str:
    """
    Обрабатывает узел секции.
    
    Использует типизированные обработчики ядра шаблонизатора
    для получения отрендеренного содержимого секции.
    
    Args:
        node: Узел секции для обработки
        template_ctx: Контекст шаблона
        
    Returns:
        Отрендеренное содержимое секции
        
    Raises:
        RuntimeError: Если обработчики не доступны или секция не найдена
    """
    # Получаем обработчики из контекста плагина
    # Плагин должен быть доступен через глобальное состояние или через контекст
    # Пока используем временное решение с получением через контекст
    handlers = getattr(template_ctx, '_processor_handlers', None)
    
    if handlers is None:
        raise RuntimeError(f"No processor handlers available for section '{node.section_name}'")
    
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


def _process_include_node_impl(node: IncludeNode, template_ctx: TemplateContext) -> str:
    """
    Обрабатывает узел включения шаблона/контекста.
    
    Использует типизированные обработчики ядра для рендеринга
    включенного AST в контексте текущего шаблона.
    
    Args:
        node: Узел включения для обработки
        template_ctx: Контекст шаблона
        
    Returns:
        Отрендеренное содержимое включения
        
    Raises:
        RuntimeError: Если включение не загружено или произошла ошибка рендеринга
    """
    if node.children is None:
        raise RuntimeError(f"Include '{node.canon_key()}' not resolved (children is None)")
    
    # Получаем обработчики из контекста
    handlers = getattr(template_ctx, '_processor_handlers', None)
    
    if handlers is None:
        raise RuntimeError("No processor handlers available in template context")
    
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


def process_section_node(node: TemplateNode, context: Any) -> str:
    """Обертка для обработчика узла секции."""
    if not isinstance(node, SectionNode):
        raise RuntimeError(f"Expected SectionNode, got {type(node)}")
    return _process_section_node_impl(node, context)


def process_include_node(node: TemplateNode, context: Any) -> str:
    """Обертка для обработчика узла включения.""" 
    if not isinstance(node, IncludeNode):
        raise RuntimeError(f"Expected IncludeNode, got {type(node)}")
    return _process_include_node_impl(node, context)


def get_processor_rules() -> List[ProcessorRule]:
    """
    Возвращает правила обработки для узлов базовых плейсхолдеров.
    
    Returns:
        Список правил обработки узлов
    """
    return [
        ProcessorRule(
            node_type=SectionNode,
            processor_func=process_section_node,
            priority=100
        ),
        ProcessorRule(
            node_type=IncludeNode, 
            processor_func=process_include_node,
            priority=100
        )
    ]


__all__ = ["process_section_node", "process_include_node", "get_processor_rules"]