"""
Центральный реестр компонентов для модульного шаблонизатора.

Управляет регистрацией и организацией плагинов, токенов, правил парсинга
и обработчиков узлов AST.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .handlers import TemplateProcessorHandlers

from .base import (
    TemplatePlugin, TokenSpec, ParsingRule, ProcessorRule,
    TokenRegistry, ParserRulesRegistry, ProcessorRegistry, PluginList
)
from .nodes import TemplateNode

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """
    Централизованный реестр всех компонентов шаблонизатора.
    
    Управляет регистрацией плагинов и их компонентов.
    Обеспечивает правильный порядок инициализации и разрешение зависимостей.
    """
    
    def __init__(self):
        """Инициализирует реестр."""
        
        # Реестры компонентов
        self.tokens: TokenRegistry = {}
        self.parser_rules: ParserRulesRegistry = {}
        self.processors: ProcessorRegistry = {}
        
        # Зарегистрированные плагины
        self.plugins: PluginList = []
        
        # Флаг инициализации
        self._plugins_initialized = False
        
        logger.debug("TemplateRegistry initialized")
    
    def register_plugin(self, plugin: TemplatePlugin) -> None:
        """
        Регистрирует плагин и все его компоненты.
        
        Args:
            plugin: Плагин для регистрации
            
        Raises:
            ValueError: Если плагин с таким именем уже зарегистрирован
        """
        if any(p.name == plugin.name for p in self.plugins):
            raise ValueError(f"Plugin '{plugin.name}' already registered")
        
        logger.debug(f"Registering plugin: {plugin.name}")
        
        # Добавляем плагин в список
        self.plugins.append(plugin)
        
        # Регистрируем компоненты плагина
        self._register_plugin_tokens(plugin)
        self._register_plugin_parser_rules(plugin)
        self._register_plugin_processors(plugin)
        
        logger.debug(f"Plugin '{plugin.name}' registered successfully")
    
    def _register_plugin_tokens(self, plugin: TemplatePlugin) -> None:
        """Регистрирует токены плагина."""
        for token_spec in plugin.register_tokens():
            if token_spec.name in self.tokens:
                logger.warning(
                    f"Token '{token_spec.name}' from plugin '{plugin.name}' "
                    f"overwrites existing token"
                )
            self.tokens[token_spec.name] = token_spec
            logger.debug(f"Registered token: {token_spec.name}")
    
    def _register_plugin_parser_rules(self, plugin: TemplatePlugin) -> None:
        """Регистрирует правила парсинга плагина."""
        for rule in plugin.register_parser_rules():
            if rule.name in self.parser_rules:
                logger.warning(
                    f"Parser rule '{rule.name}' from plugin '{plugin.name}' "
                    f"overwrites existing rule"
                )
            self.parser_rules[rule.name] = rule
            logger.debug(f"Registered parser rule: {rule.name}")
    
    def _register_plugin_processors(self, plugin: TemplatePlugin) -> None:
        """Регистрирует обработчики узлов плагина."""
        for processor_rule in plugin.register_processors():
            node_type = processor_rule.node_type
            if node_type not in self.processors:
                self.processors[node_type] = []
            
            # Вставляем с учетом приоритета
            self.processors[node_type].append(processor_rule)
            self.processors[node_type].sort(key=lambda r: r.priority, reverse=True)
            
            logger.debug(
                f"Registered processor for {node_type.__name__} "
                f"(priority: {processor_rule.priority})"
            )
    
    def initialize_plugins(self, handlers: Optional['TemplateProcessorHandlers'] = None) -> None:
        """
        Инициализирует все зарегистрированные плагины.
        
        Args:
            handlers: Обработчики ядра шаблонизатора для передачи плагинам
        
        Вызывается после регистрации всех плагинов для установки
        зависимостей и финальной настройки.
        """
        if self._plugins_initialized:
            return
            
        logger.debug("Initializing plugins...")
        
        # Сортируем плагины по приоритету
        sorted_plugins = sorted(self.plugins, key=lambda p: p.priority, reverse=True)
        
        # Устанавливаем обработчики для плагинов
        if handlers is not None:
            for plugin in sorted_plugins:
                plugin.set_handlers(handlers)
                logger.debug(f"Handlers set for plugin '{plugin.name}'")
        
        # Инициализируем плагины в порядке приоритета
        for plugin in sorted_plugins:
            try:
                plugin.initialize()
                logger.debug(f"Plugin '{plugin.name}' initialized")
            except Exception as e:
                logger.error(f"Failed to initialize plugin '{plugin.name}': {e}")
                raise
        
        self._plugins_initialized = True
        logger.debug("All plugins initialized successfully")
    
    def get_sorted_parser_rules(self) -> List[ParsingRule]:
        """
        Возвращает правила парсинга, отсортированные по приоритету.
        
        Returns:
            Список правил в порядке убывания приоритета
        """
        active_rules = [rule for rule in self.parser_rules.values() if rule.enabled]
        return sorted(active_rules, key=lambda r: r.priority, reverse=True)
    
    def get_processors_for_node(self, node_type: Type[TemplateNode]) -> List[ProcessorRule]:
        """
        Возвращает обработчики для указанного типа узла.
        
        Args:
            node_type: Тип узла для поиска обработчиков
            
        Returns:
            Список обработчиков в порядке убывания приоритета
        """
        return self.processors.get(node_type, [])
    
    def get_tokens_by_priority(self) -> List[TokenSpec]:
        """
        Возвращает токены, отсортированные по приоритету.
        
        Returns:
            Список спецификаций токенов в порядке убывания приоритета
        """
        return sorted(self.tokens.values(), key=lambda t: t.priority, reverse=True)
    
    def get_plugin_by_name(self, name: str) -> Optional[TemplatePlugin]:
        """
        Возвращает плагин по имени.
        
        Args:
            name: Имя плагина
            
        Returns:
            Плагин или None если не найден
        """
        return next((p for p in self.plugins if p.name == name), None)
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализированы ли плагины."""
        return self._plugins_initialized
    
    def get_stats(self) -> Dict[str, int]:
        """
        Возвращает статистику по зарегистрированным компонентам.
        
        Returns:
            Словарь со статистикой
        """
        processor_count = sum(len(rules) for rules in self.processors.values())
        
        return {
            "plugins": len(self.plugins),
            "tokens": len(self.tokens),
            "parser_rules": len(self.parser_rules),
            "processors": processor_count,
            "node_types_with_processors": len(self.processors),
        }


__all__ = ["TemplateRegistry"]