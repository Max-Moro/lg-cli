"""
Плагин для обработки общих плейсхолдеров секций и шаблонов.

Блок №1 модульного шаблонизатора - обработка базовых плейсхолдеров:
- ${section_name} - вставка секций
- ${tpl:template_name} - вставка шаблонов  
- ${ctx:context_name} - вставка контекстов
- Поддержка адресных ссылок (@origin:name)
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..base import TemplatePlugin, PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ParsingContext
from ..nodes import TextNode, TemplateNode
from ..tokens import TokenType

class CommonPlaceholdersPlugin(TemplatePlugin):
    """
    Плагин для обработки плейсхолдеров секций и шаблонов.
    
    Предоставляет базовую функциональность для обработки ${...} плейсхолдеров
    в модульном шаблонизаторе.
    """
    
    @property
    def name(self) -> str:
        return "common_placeholders"
    
    @property
    def priority(self) -> PluginPriority:
        return PluginPriority.PLACEHOLDER
    
    def register_tokens(self) -> List[TokenSpec]:
        """Регистрирует токены для плейсхолдеров."""
        return [
            TokenSpec(
                name="PLACEHOLDER_START",
                pattern=re.compile(r'\$\{'),
                priority=int(PluginPriority.PLACEHOLDER)
            ),
            TokenSpec(
                name="PLACEHOLDER_END", 
                pattern=re.compile(r'\}'),
                priority=int(PluginPriority.PLACEHOLDER)
            ),
        ]
    
    def register_parser_rules(self) -> List[ParsingRule]:
        """Регистрирует правила парсинга для плейсхолдеров."""
        return [
            ParsingRule(
                name="parse_placeholder",
                priority=PluginPriority.PLACEHOLDER,
                parser_func=self._parse_placeholder
            ),
        ]
    
    def register_processors(self) -> List[ProcessorRule]:
        """Регистрирует обработчики для узлов плейсхолдеров."""
        # Пока возвращаем пустой список - обработка будет в следующих фазах
        return []
    
    def _parse_placeholder(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Парсит плейсхолдер ${...}.
        
        Базовая заглушка - пока создает TextNode с содержимым плейсхолдера.
        В последующих фазах будет реализована полная логика.
        """
        if not context.match(TokenType.PLACEHOLDER_START):
            return None
        
        # Потребляем ${
        context.advance()
        
        # Собираем содержимое до }
        content_parts = []
        while not context.is_at_end() and not context.match(TokenType.PLACEHOLDER_END):
            token = context.advance()
            content_parts.append(token.value)
        
        # Потребляем }
        if context.match(TokenType.PLACEHOLDER_END):
            context.advance()
        
        # Пока просто возвращаем как текст (заглушка)
        placeholder_content = "".join(content_parts)
        return TextNode(text=f"${{{placeholder_content}}}")


__all__ = ["CommonPlaceholdersPlugin"]