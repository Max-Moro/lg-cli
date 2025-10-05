"""
Правила обработки для адаптивных конструкций в шаблонах.

Обрабатывает условные блоки, режимные блоки и комментарии.
"""

from __future__ import annotations

from typing import Callable, List

from .nodes import ConditionalBlockNode, ModeBlockNode, CommentNode
from ..types import ProcessorRule, ProcessingContext
from ...template.context import TemplateContext

# Тип функтора для обработки узла AST
ProcessASTNodeFunc = Callable[[ProcessingContext], str]


class AdaptiveProcessorRules:
    """
    Класс правил обработки для адаптивных конструкций.
    
    Инкапсулирует все правила обработки с доступом к функтору
    обработки узлов через состояние экземпляра.
    """
    
    def __init__(self, process_ast_node: ProcessASTNodeFunc, template_ctx: TemplateContext):
        """
        Инициализирует правила обработки.
        
        Args:
            process_ast_node: Функтор для обработки узлов AST
            template_ctx: Контекст шаблона для управления состоянием
        """
        self.process_ast_node = process_ast_node
        self.template_ctx = template_ctx
    
    def process_conditional(self, processing_context: ProcessingContext) -> str:
        """
        Обрабатывает условный блок {% if ... %}.
        
        Вычисляет условие и возвращает соответствующее содержимое.
        """
        node = processing_context.get_node()
        if not isinstance(node, ConditionalBlockNode):
            raise RuntimeError(f"Expected ConditionalBlockNode, got {type(node)}")
        
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
    
    def process_mode_block(self, processing_context: ProcessingContext) -> str:
        """
        Обрабатывает режимный блок {% mode ... %}.
        
        Переключает режим и обрабатывает тело блока с новым режимом.
        """
        node = processing_context.get_node()
        if not isinstance(node, ModeBlockNode):
            raise RuntimeError(f"Expected ModeBlockNode, got {type(node)}")
        
        # Входим в режимный блок
        self.template_ctx.enter_mode_block(node.modeset, node.mode)
        
        try:
            # Рендерим тело блока с активным режимом
            result = self._render_body(node.body)
        finally:
            # Всегда выходим из блока, даже при ошибке
            self.template_ctx.exit_mode_block()
        
        return result
    
    def process_comment(self, processing_context: ProcessingContext) -> str:
        """
        Обрабатывает комментарий {# ... #}.
        
        Комментарии не попадают в вывод.
        """
        node = processing_context.get_node()
        if not isinstance(node, CommentNode):
            raise RuntimeError(f"Expected CommentNode, got {type(node)}")
        
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
        
        for i, child_node in enumerate(body):
            # Создаем контекст обработки для каждого узла
            processing_context = ProcessingContext(ast=body, node_index=i)
            rendered = self.process_ast_node(processing_context)
            if rendered:
                result_parts.append(rendered)
        
        return "".join(result_parts)


def get_adaptive_processor_rules(
    process_ast_node: ProcessASTNodeFunc,
    template_ctx: TemplateContext
) -> List[ProcessorRule]:
    """
    Возвращает правила обработки для адаптивных конструкций.
    
    Args:
        process_ast_node: Функтор для обработки узлов AST
        template_ctx: Контекст шаблона для управления состоянием
        
    Returns:
        Список правил обработки с привязанными функторами
    """
    rules_instance = AdaptiveProcessorRules(process_ast_node, template_ctx)
    
    return [
        ProcessorRule(
            node_type=ConditionalBlockNode,
            processor_func=rules_instance.process_conditional
        ),
        ProcessorRule(
            node_type=ModeBlockNode,
            processor_func=rules_instance.process_mode_block
        ),
        ProcessorRule(
            node_type=CommentNode,
            processor_func=rules_instance.process_comment
        ),
        # ElifBlockNode не обрабатывается отдельно - он часть ConditionalBlockNode
    ]


__all__ = ["AdaptiveProcessorRules", "ProcessASTNodeFunc", "get_adaptive_processor_rules"]
