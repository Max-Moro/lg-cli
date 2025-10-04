"""
Плагин для обработки Markdown-плейсхолдеров.

Регистрирует все необходимые токены, правила парсинга и обработчики
для поддержки ${md:path}, ${md@origin:path}, глобов, якорей и параметров.
"""

from __future__ import annotations

from typing import List

from .nodes import MarkdownFileNode
from .parser_rules import get_md_parser_rules
from .tokens import get_md_token_specs
from .virtual_sections import VirtualSectionFactory
from ..base import TemplatePlugin
from ..nodes import TemplateNode
from ..types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule
from ...template import TemplateContext


class MdPlaceholdersPlugin(TemplatePlugin):
    """
    Плагин для обработки Markdown-плейсхолдеров.
    
    Обеспечивает функциональность:
    - ${md:path} - прямое включение Markdown-файла
    - ${md:path#anchor} - включение конкретной секции
    - ${md:path,level:3,strip_h1:true} - включение с параметрами
    - ${md@origin:path} - адресные ссылки на файлы в других скоупах
    - ${md:docs/*} - глобы для включения множества файлов
    - ${md:path,if:tag:condition} - условные включения
    """

    def __init__(self, template_ctx: TemplateContext):
        """
        Инициализирует плагин с контекстом шаблона.

        Args:
            template_ctx: Контекст шаблона для управления состоянием
        """
        super().__init__()
        self.template_ctx = template_ctx
        
        # Фабрика виртуальных секций (создается один раз)
        self.virtual_factory = VirtualSectionFactory()

    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "md_placeholders"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.PLACEHOLDER
    
    def initialize(self) -> None:
        """Добавляет md-специфичные токены в контекст плейсхолдеров."""
        # Добавляем токены в существующий контекст плейсхолдеров
        self.registry.register_tokens_in_context(
            "placeholder",  # Используем существующий контекст
            ["MD_PREFIX", "HASH", "COMMA", "BOOL_TRUE", "BOOL_FALSE", "NUMBER", "GLOB_STAR"]
        )
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для MD-плейсхолдеров."""
        return get_md_token_specs()

    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга MD-плейсхолдеров."""
        return get_md_parser_rules()

    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Создает замыкания над типизированными обработчиками для обработки MD-узлов.
        """
        def process_markdown_node(node: TemplateNode) -> str:
            """Обрабатывает узел MarkdownFileNode через виртуальную секцию."""
            if not isinstance(node, MarkdownFileNode):
                raise RuntimeError(f"Expected MarkdownFileNode, got {type(node)}")
            
            # Проверяем условие включения если оно задано
            if node.condition:
                should_include = self.template_ctx.evaluate_condition_text(node.condition)
                if not should_include:
                    # Условие не выполнено - пропускаем узел
                    return ""

            # TODO: Нужно получить AST и node_index для анализа контекста заголовков
            # Пока используем дефолтные значения
            from .heading_context import HeadingContext
            heading_context = HeadingContext(
                placeholders_continuous_chain=False,
                placeholder_inside_heading=False,
                heading_level=2,
                strip_h1=True
            )

            section_config, section_ref = self.virtual_factory.create_for_markdown_file(
                node=node,
                repo_root=self.template_ctx.run_ctx.root,
                heading_context=heading_context
            )

            # Устанавливаем виртуальную секцию в контекст
            self.template_ctx.set_virtual_section(section_config)

            try:
                # Обрабатываем через section_handler
                result = self.handlers.process_section_ref(section_ref)
                return result
            finally:
                # Всегда очищаем виртуальную секцию после обработки
                self.template_ctx.clear_virtual_section()
        
        return [
            ProcessorRule(
                node_type=MarkdownFileNode,
                processor_func=process_markdown_node,
                priority=100
            )
        ]


__all__ = ["MdPlaceholdersPlugin"]
