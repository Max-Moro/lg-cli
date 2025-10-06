"""
Плагин для обработки task-плейсхолдеров.
"""

from __future__ import annotations

from typing import List

from .nodes import TaskNode
from .parser_rules import get_task_parser_rules
from .tokens import get_task_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ProcessingContext
from ...template import TemplateContext


class TaskPlaceholderPlugin(TemplatePlugin):
    """
    Плагин для обработки task-плейсхолдеров.
    
    Обеспечивает функциональность:
    - ${task} - простая вставка текста задачи
    - ${task:prompt:"default text"} - вставка с дефолтным значением
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Инициализирует плагин с контекстом шаблона.

        Args:
            template_ctx: Контекст шаблона для управления состоянием
        """
        super().__init__()
        self.template_ctx = template_ctx

    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "task_placeholder"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.PLACEHOLDER
    
    def initialize(self) -> None:
        """Добавляет task-специфичные токены в контекст плейсхолдеров."""
        # Добавляем токены в существующий контекст плейсхолдеров
        self.registry.register_tokens_in_context(
            "placeholder",
            ["TASK_KEYWORD", "PROMPT_KEYWORD", "STRING_LITERAL"]
        )
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для task-плейсхолдеров."""
        return get_task_token_specs()

    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга task-плейсхолдеров."""
        return get_task_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        """
        def process_task_node(processing_context: ProcessingContext) -> str:
            """Обрабатывает узел TaskNode."""
            node = processing_context.get_node()
            if not isinstance(node, TaskNode):
                raise RuntimeError(f"Expected TaskNode, got {type(node)}")
            
            # Получаем task_text из RunContext через TemplateContext
            task_text = self.template_ctx.run_ctx.options.task_text
            
            # Если task_text задан и непустой - возвращаем его
            if task_text:
                return task_text
            
            # Если task_text не задан и есть default_prompt - возвращаем его
            if node.default_prompt is not None:
                return node.default_prompt
            
            # Иначе возвращаем пустую строку
            return ""
        
        return [
            ProcessorRule(
                node_type=TaskNode,
                processor_func=process_task_node
            )
        ]


__all__ = ["TaskPlaceholderPlugin"]