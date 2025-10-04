"""
Плагин для обработки базовых плейсхолдеров секций и шаблонов.

Регистрирует все необходимые токены, правила парсинга и обработчики
для поддержки ${section}, ${tpl:name}, ${ctx:name} и адресных ссылок.
"""

from __future__ import annotations

from typing import List

from .nodes import SectionNode, IncludeNode
from .parser_rules import get_placeholder_parser_rules
from .tokens import get_placeholder_token_specs
from ..base import TemplatePlugin
from ..nodes import TemplateNode
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenContext
from ...template import TemplateContext


class CommonPlaceholdersPlugin(TemplatePlugin):
    """
    Плагин для обработки базовых плейсхолдеров секций и шаблонов.
    
    Обеспечивает функциональность:
    - ${section_name} - вставка секций
    - ${tpl:template_name} - включение шаблонов
    - ${ctx:context_name} - включение контекстов  
    - Адресные ссылки @origin:name для межскоуповых включений
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Инициализирует плагин с контекстом шаблона.

        Args:
            template_ctx: Контекст шаблона для управления состоянием
        """
        super().__init__()
        self.template_ctx = template_ctx
        # Резолвер будет создан один раз при инициализации
        self._resolver = None

    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "common_placeholders"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.PLACEHOLDER
    
    def initialize(self) -> None:
        """Инициализирует резолвер после установки всех зависимостей."""
        from .resolver import CommonPlaceholdersResolver
        run_ctx = self.template_ctx.run_ctx
        # Передаем template_ctx для управления origin через TemplateState
        self._resolver = CommonPlaceholdersResolver(run_ctx, self.handlers, self.registry)
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для плейсхолдеров."""
        return get_placeholder_token_specs()

    def register_token_contexts(self) -> List[TokenContext]:
        """Регистрирует контексты токенов для плейсхолдеров."""
        return [TokenContext(
            name="placeholder",
            open_tokens={"PLACEHOLDER_START"},
            close_tokens={"PLACEHOLDER_END"},
            inner_tokens={
                "IDENTIFIER", "COLON", "AT", "LBRACKET", "RBRACKET", "WHITESPACE"
            },
            allow_nesting=False,
        )]

    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга плейсхолдеров."""
        return get_placeholder_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Создает замыкания над типизированными обработчиками для прямой обработки узлов.
        """
        def process_section_node(node: TemplateNode) -> str:
            """Обрабатывает узел секции через типизированные обработчики."""
            if not isinstance(node, SectionNode):
                raise RuntimeError(f"Expected SectionNode, got {type(node)}")
            
            # Проверяем, что узел был резолвлен
            if node.resolved_ref is None:
                raise RuntimeError(f"Section node '{node.section_name}' not resolved")
            
            # Используем типизированный обработчик секций
            return self.handlers.process_section_ref(node.resolved_ref)
        
        def process_include_node(node: TemplateNode) -> str:
            """Обрабатывает узел включения через типизированные обработчики."""
            if not isinstance(node, IncludeNode):
                raise RuntimeError(f"Expected IncludeNode, got {type(node)}")
            
            # Проверяем, что включение было загружено
            if node.children is None:
                raise RuntimeError(f"Include '{node.canon_key()}' not resolved")
            
            # Рендерим дочерние узлы
            result_parts = []
            for child_node in node.children:
                rendered = self.handlers.process_ast_node(child_node)
                if rendered:
                    result_parts.append(rendered)
            
            return "".join(result_parts)
        
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
    
    def register_resolvers(self) -> List[ResolverRule]:
        """
        Регистрирует резолверы узлов AST для базовых плейсхолдеров.
        """
        def resolve_section_or_include(node: TemplateNode, context: str) -> TemplateNode:
            """Резолвит узлы SectionNode и IncludeNode."""
            if not isinstance(node, (SectionNode, IncludeNode)):
                # Не наш узел
                return node
            
            # Используем единственный экземпляр резолвера (с сохраненным стеком)
            if self._resolver is None:
                raise RuntimeError("Resolver not initialized. Call initialize() first.")
            return self._resolver.resolve_node(node, context)
        
        return [
            ResolverRule(
                node_type=SectionNode,
                resolver_func=resolve_section_or_include,
                priority=100
            ),
            ResolverRule(
                node_type=IncludeNode,
                resolver_func=resolve_section_or_include,
                priority=100
            )
        ]


__all__ = ["CommonPlaceholdersPlugin"]