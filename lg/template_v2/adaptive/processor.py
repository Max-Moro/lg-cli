"""
Обработчики узлов AST для адаптивных конструкций.

Реализует логику выполнения условных блоков, режимных блоков и комментариев.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .nodes import ConditionalBlockNode, ElifBlockNode, ModeBlockNode, CommentNode

if TYPE_CHECKING:
    from ..handlers import TemplateProcessorHandlers
    from ...template.context import TemplateContext


class AdaptiveProcessor:
    """
    Процессор для обработки адаптивных узлов AST.
    
    Реализует вычисление условий, управление режимами и обработку комментариев.
    """
    
    def __init__(self, handlers: TemplateProcessorHandlers, template_ctx: 'TemplateContext'):
        """
        Инициализирует процессор адаптивных конструкций.
        
        Args:
            handlers: Обработчики ядра шаблонизатора
            template_ctx: Контекст шаблона для управления состоянием
        """
        self.handlers = handlers
        self.template_ctx = template_ctx
    
    def process_conditional(self, node: ConditionalBlockNode) -> str:
        """
        Обрабатывает условный блок {% if ... %}.
        
        Вычисляет условие и возвращает соответствующее содержимое.
        """
        # Вычисляем основное условие
        if node.condition_ast:
            condition_result = self.template_ctx.evaluate_condition(node.condition_ast)
        else:
            # Fallback на текстовое вычисление
            condition_result = self.template_ctx.evaluate_condition_text(node.condition_text)
        
        # Если основное условие истинно, рендерим тело if
        if condition_result:
            return self._render_body(node.body)
        
        # Проверяем elif блоки
        for elif_block in node.elif_blocks:
            if elif_block.condition_ast:
                elif_result = self.template_ctx.evaluate_condition(elif_block.condition_ast)
            else:
                elif_result = self.template_ctx.evaluate_condition_text(elif_block.condition_text)
            
            if elif_result:
                return self._render_body(elif_block.body)
        
        # Если все условия ложны, рендерим else блок если есть
        if node.else_block:
            return self._render_body(node.else_block.body)
        
        # Все условия ложны и нет else - возвращаем пустую строку
        return ""
    
    def process_mode_block(self, node: ModeBlockNode) -> str:
        """
        Обрабатывает режимный блок {% mode ... %}.
        
        Переключает режим и обрабатывает тело блока с новым режимом.
        """
        # Входим в режимный блок
        self.template_ctx.enter_mode_block(node.modeset, node.mode)
        
        try:
            # Рендерим тело блока с активным режимом
            result = self._render_body(node.body)
        finally:
            # Всегда выходим из блока, даже при ошибке
            self.template_ctx.exit_mode_block()
        
        return result
    
    def process_comment(self, node: CommentNode) -> str:
        """
        Обрабатывает комментарий {# ... #}.
        
        Комментарии не попадают в вывод.
        """
        # Комментарии игнорируются при рендеринге
        return ""
    
    def _render_body(self, body: list) -> str:
        """
        Рендерит список узлов в теле блока.
        
        Args:
            body: Список узлов для рендеринга
            
        Returns:
            Отрендеренное содержимое
        """
        result_parts = []
        
        for child_node in body:
            rendered = self.handlers.process_ast_node(child_node)
            if rendered:
                result_parts.append(rendered)
        
        return "".join(result_parts)


__all__ = ["AdaptiveProcessor"]

