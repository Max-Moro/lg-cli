"""
Центральный реестр компонентов для модульного шаблонизатора.

Управляет регистрацией и организацией плагинов, токенов, правил парсинга
и обработчиков узлов AST.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Type

from .base import TemplatePlugin, PluginList
from .handlers import TemplateProcessorHandlers
from .nodes import TemplateNode
from .protocols import TemplateRegistryProtocol
from .tokens import TokenType
from .types import TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenRegistry, ParserRulesRegistry, \
    ProcessorRegistry, ResolverRegistry, TokenContext

logger = logging.getLogger(__name__)


class TemplateRegistry(TemplateRegistryProtocol):
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
        self.resolvers: ResolverRegistry = {}
        
        # Реестр контекстных групп токенов
        self.token_contexts: Dict[str, TokenContext] = {}
        
        # Зарегистрированные плагины
        self.plugins: PluginList = []
        
        # Флаг инициализации
        self._plugins_initialized = False
        
        # Регистрируем базовые токены
        self._register_builtin_tokens()
        
        logger.debug("TemplateRegistry initialized")

    def _register_builtin_tokens(self) -> None:
        """Регистрирует встроенные токены, не зависящие от плагинов."""
        # Токен для непрерывного текста (между специальными конструкциями)
        # Захватывает один или более символов, не являющихся началом специальных конструкций
        # Останавливается перед: ${, {%, {#
        text_token = TokenSpec(
            name=TokenType.TEXT.value,
            pattern=re.compile(r'(?:\$(?!\{)|\{(?![%#])|[^${])+'),  # Не $ перед {, не { перед % или #, или любой другой символ
        )
        self.tokens[TokenType.TEXT.value] = text_token
        logger.debug("Registered builtin TEXT token")
    
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
        self._register_plugin_token_contexts(plugin)
        self._register_plugin_parser_rules(plugin)
        self._register_plugin_processors(plugin)
        self._register_plugin_resolvers(plugin)

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

    def _register_plugin_token_contexts(self, plugin: TemplatePlugin) -> None:
        """Регистрирует контекстные группы токенов плагина."""
        for context in plugin.register_token_contexts():
            self.token_contexts[context.name] = context
            logger.debug(f"Registered token context '{context.name}' from plugin '{plugin.name}'")

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
            self.processors[node_type].append(processor_rule)
            logger.debug(f"Registered processor for {node_type.__name__}")
    
    def _register_plugin_resolvers(self, plugin: TemplatePlugin) -> None:
        """Регистрирует резолверы узлов плагина."""
        for resolver_rule in plugin.register_resolvers():
            node_type = resolver_rule.node_type
            if node_type not in self.resolvers:
                self.resolvers[node_type] = []
            self.resolvers[node_type].append(resolver_rule)
            logger.debug(f"Registered resolver for {node_type.__name__}")

    def initialize_plugins(self, handlers: TemplateProcessorHandlers) -> None:
        """
        Инициализирует все зарегистрированные плагины.
        
        Args:
            handlers: Обработчики ядра шаблонизатора для передачи плагинам
        
        Вызывается после регистрации всех плагинов для установки
        зависимостей и финальной настройки.
        """
        if self._plugins_initialized:
            return

        # Сортируем плагины по приоритету
        sorted_plugins = sorted(self.plugins, key=lambda p: p.priority, reverse=True)
        
        # Устанавливаем обработчики и сам регистратор для плагинов
        for plugin in sorted_plugins:
            plugin.set_registry(self)
            plugin.set_handlers(handlers)
        
        # Инициализируем плагины в порядке приоритета (они могут произвести дополнительную тонкую регистрацию)
        for plugin in sorted_plugins:
            plugin.initialize()
        
        self._plugins_initialized = True
    
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
    
    def get_resolvers_for_node(self, node_type: Type[TemplateNode]) -> List[ResolverRule]:
        """
        Возвращает резолверы для указанного типа узла.
        
        Args:
            node_type: Тип узла для поиска резолверов
            
        Returns:
            Список резолверов в порядке убывания приоритета
        """
        return self.resolvers.get(node_type, [])
    
    def get_tokens_by_priority(self) -> List[TokenSpec]:
        """
        Возвращает токены в правильном порядке для контекстуального лексера.
        
        Специальные токены (открывающие/закрывающие) должны проверяться раньше TEXT.
        
        Returns:
            Список спецификаций токенов в правильном порядке
        """
        # Разделяем токены по типам
        special_tokens = []
        text_tokens = []
        
        for token_spec in self.tokens.values():
            if token_spec.name == TokenType.TEXT.value:
                text_tokens.append(token_spec)
            else:
                special_tokens.append(token_spec)
        
        # Специальные токены первыми, TEXT токены последними
        return special_tokens + text_tokens
    
    def register_tokens_in_context(self, context_name: str, token_names: List[str]) -> None:
        """
        Добавляет токены в существующий контекст.
        
        Args:
            context_name: Имя существующего контекста
            token_names: Имена токенов для добавления в контекст
            
        Raises:
            ValueError: Если контекст не найден
        """
        if context_name not in self.token_contexts:
            raise ValueError(f"Token context '{context_name}' not found")
        
        context = self.token_contexts[context_name]
        # Создаем новый контекст с обновленными токенами
        self.token_contexts[context_name] = TokenContext(
            name=context.name,
            open_tokens=context.open_tokens,
            close_tokens=context.close_tokens,
            inner_tokens=context.inner_tokens | set(token_names),
            allow_nesting=context.allow_nesting,
        )
        
        logger.debug(f"Added {len(token_names)} tokens to context '{context_name}'")
    
    def get_all_token_contexts(self) -> List[TokenContext]:
        """
        Возвращает все зарегистрированные контексты токенов.
        
        Returns:
            Список всех контекстов
        """
        return list(self.token_contexts.values())


__all__ = ["TemplateRegistry"]