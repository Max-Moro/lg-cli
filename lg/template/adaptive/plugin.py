"""
Плагин для адаптивных возможностей шаблонизатора.

Регистрирует все необходимые токены, правила парсинга и обработчики
для поддержки условных конструкций, режимных блоков и комментариев.
"""

from __future__ import annotations

from typing import List

from .nodes import ConditionalBlockNode, ModeBlockNode, CommentNode
from .parser_rules import get_adaptive_parser_rules, set_parser_handlers
from .processor import AdaptiveProcessor
from .tokens import get_adaptive_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, TokenContext, ProcessingContext
from ...template.context import TemplateContext


class AdaptivePlugin(TemplatePlugin):
    """
    Плагин для адаптивных возможностей шаблонизатора.
    
    Обеспечивает функциональность:
    - {% if condition %}...{% elif %}...{% else %}...{% endif %} - условные конструкции
    - {% mode modeset:mode %}...{% endmode %} - режимные блоки  
    - {# комментарий #} - комментарии
    - Логические операторы AND, OR, NOT
    - Операторы условий: tag:name, TAGSET:set:tag, scope:local
    """
    
    def __init__(self, template_ctx: TemplateContext):
        """
        Инициализирует плагин с контекстом шаблона.
        
        Args:
            template_ctx: Контекст шаблона для управления состоянием
        """
        super().__init__()
        self.template_ctx = template_ctx
        self._processor = None
    
    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "adaptive"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.DIRECTIVE
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для адаптивных конструкций."""
        return get_adaptive_token_specs()
    
    def register_token_contexts(self) -> List[TokenContext]:
        """Регистрирует контексты токенов для адаптивных конструкций."""
        return [
            TokenContext(
                name="directive",
                open_tokens={"DIRECTIVE_START"},
                close_tokens={"DIRECTIVE_END"},
                inner_tokens={
                    "IDENTIFIER", "COLON", "LPAREN", "RPAREN", "WHITESPACE"
                },
                allow_nesting=False,
            ),
            TokenContext(
                name="comment",
                open_tokens={"COMMENT_START"},
                close_tokens={"COMMENT_END"},
                inner_tokens=set(),  # Внутри комментария все - текст
                allow_nesting=False,
            )
        ]
    
    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга адаптивных конструкций."""
        return get_adaptive_parser_rules()
    
    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Создает замыкания над AdaptiveProcessor для обработки узлов.
        Процессор будет создан позже в initialize(), когда обработчики будут установлены.
        """
        # Используем ленивое создание процессора через замыкание
        def get_processor():
            if self._processor is None:
                raise RuntimeError("Processor not initialized. Call initialize() first.")
            return self._processor
        
        def process_conditional_node(processing_context: ProcessingContext) -> str:
            """Обрабатывает условный узел."""
            node = processing_context.get_node()
            if not isinstance(node, ConditionalBlockNode):
                raise RuntimeError(f"Expected ConditionalBlockNode, got {type(node)}")
            return get_processor().process_conditional(node)
        
        def process_mode_node(processing_context: ProcessingContext) -> str:
            """Обрабатывает режимный узел."""
            node = processing_context.get_node()
            if not isinstance(node, ModeBlockNode):
                raise RuntimeError(f"Expected ModeBlockNode, got {type(node)}")
            return get_processor().process_mode_block(node)
        
        def process_comment_node(processing_context: ProcessingContext) -> str:
            """Обрабатывает комментарий."""
            node = processing_context.get_node()
            if not isinstance(node, CommentNode):
                raise RuntimeError(f"Expected CommentNode, got {type(node)}")
            return get_processor().process_comment(node)
        
        return [
            ProcessorRule(
                node_type=ConditionalBlockNode,
                processor_func=process_conditional_node
            ),
            ProcessorRule(
                node_type=ModeBlockNode,
                processor_func=process_mode_node
            ),
            ProcessorRule(
                node_type=CommentNode,
                processor_func=process_comment_node
            ),
            # ElifBlockNode не обрабатывается отдельно - он часть ConditionalBlockNode
        ]
    
    def initialize(self) -> None:
        """
        Инициализирует плагин после регистрации всех компонентов.
        
        Создает процессор и устанавливает обработчики для правил парсинга.
        """
        # Создаем процессор теперь, когда обработчики установлены
        if self._processor is None:
            self._processor = AdaptiveProcessor(self.handlers, self.template_ctx)
        
        # Устанавливаем обработчики для использования в правилах парсинга
        set_parser_handlers(self.handlers)


__all__ = ["AdaptivePlugin"]

