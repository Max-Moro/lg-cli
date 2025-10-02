"""
Главный плагин для обработки базовых плейсхолдеров секций и шаблонов.

Регистрирует все необходимые токены, правила парсинга и обработчики
для поддержки ${section}, ${tpl:name}, ${ctx:name} и адресных ссылок.
"""

from __future__ import annotations

from typing import List

from ..base import TemplatePlugin, TokenSpec, ParsingRule, ProcessorRule, PluginPriority
from .tokens import get_placeholder_token_specs  
from .parser_rules import get_placeholder_parser_rules
from .processor import get_processor_rules


class CommonPlaceholdersPlugin(TemplatePlugin):
    """
    Плагин для обработки базовых плейсхолдеров секций и шаблонов.
    
    Обеспечивает функциональность:
    - ${section_name} - вставка секций
    - ${tpl:template_name} - включение шаблонов
    - ${ctx:context_name} - включение контекстов  
    - Адресные ссылки @origin:name для межскоуповых включений
    """
    
    def __init__(self):
        """Инициализирует плагин."""
        super().__init__()
    
    @property
    def name(self) -> str:
        """Возвращает имя плагина."""
        return "common_placeholders"
    
    @property
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        return PluginPriority.PLACEHOLDER
    
    def register_tokens(self) -> List[TokenSpec]:
        """
        Регистрирует токены для плейсхолдеров.
        
        Returns:
            Список спецификаций токенов
        """
        return get_placeholder_token_specs()
    
    def register_parser_rules(self) -> List[ParsingRule]:
        """
        Регистрирует правила парсинга плейсхолдеров.
        
        Returns:
            Список правил парсинга
        """
        return get_placeholder_parser_rules()
    
    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Returns:
            Список правил обработки
        """
        return get_processor_rules()
    
    def initialize(self) -> None:
        """
        Инициализирует плагин после регистрации всех компонентов.
        
        Выполняет дополнительную настройку если необходимо.
        """
        # Пока дополнительной инициализации не требуется
        pass


__all__ = ["CommonPlaceholdersPlugin"]