"""
Плагин для адаптивных возможностей шаблонизатора.

Регистрирует все необходимые токены, правила парсинга и обработчики
для поддержки условных конструкций, режимных блоков и комментариев.
"""

from __future__ import annotations

from typing import List

from .parser_rules import get_adaptive_parser_rules
from .processor_rules import get_adaptive_processor_rules
from .tokens import get_adaptive_token_specs
from ..base import TemplatePlugin
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, TokenContext
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
        """
        Регистрирует правила парсинга адаптивных конструкций.
        
        Использует замыкание для ленивого доступа к handlers.parse_next_node.
        """
        return get_adaptive_parser_rules(lambda ctx: self.handlers.parse_next_node(ctx))
    
    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Использует замыкания для ленивого доступа к handlers.
        """
        return get_adaptive_processor_rules(
            process_ast_node=lambda ctx: self.handlers.process_ast_node(ctx),
            template_ctx=self.template_ctx
        )


__all__ = ["AdaptivePlugin"]

