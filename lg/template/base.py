"""
Базовые интерфейсы и абстракции для модульного шаблонизатора.

Определяет базовые классы и интерфейсы, которые должны реализовывать
плагины для интеграции в систему шаблонизации.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .handlers import TemplateProcessorHandlers
from .protocols import TemplateRegistryProtocol
# Импортируем собственные типы
from .types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenContext


class TemplatePlugin(ABC):
    """
    Базовый интерфейс для плагинов шаблонизатора.
    
    Каждый плагин должен реализовать этот интерфейс для регистрации
    своих компонентов в системе шаблонизации.
    """
    
    def __init__(self):
        """Инициализирует плагин."""
        self._handlers: Optional[TemplateProcessorHandlers] = None
        self._registry: Optional[TemplateRegistryProtocol] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Возвращает имя плагина."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина."""
        pass
    
    def set_handlers(self, handlers: TemplateProcessorHandlers) -> None:
        """
        Устанавливает обработчики ядра шаблонизатора.
        
        Args:
            handlers: Внутренние обработчики для вызова функций ядра
        """
        self._handlers = handlers
    
    @property
    def handlers(self) -> TemplateProcessorHandlers:
        """
        Возвращает обработчики ядра шаблонизатора.
        
        Returns:
            Обработчики для вызова функций ядра
        """
        assert self._handlers is not None, "Handlers must be set before use"
        return self._handlers
    
    def set_registry(self, registry: TemplateRegistryProtocol) -> None:
        """
        Устанавливает реестр шаблонизатора для плагина.
        
        Args:
            registry: Реестр для доступа к расширению контекстов
        """
        self._registry = registry
    
    @property
    def registry(self) -> TemplateRegistryProtocol:
        """
        Возвращает реестр шаблонизатора.
        
        Returns:
            Реестр для вызова функций расширения контекстов
        """
        assert self._registry is not None, "Registry must be set before use"
        return self._registry
    
    @abstractmethod
    def register_tokens(self) -> List[TokenSpec]:
        """
        Регистрирует токены, которые должен распознавать лексер.
        
        Returns:
            Список спецификаций токенов
        """
        pass

    def register_token_contexts(self) -> List[TokenContext]:
        """
        Регистрирует контекстные группы токенов.

        Returns:
            Список контекстов токенов
        """
        return []

    @abstractmethod
    def register_parser_rules(self) -> List[ParsingRule]:
        """
        Регистрирует правила парсинга для создания узлов AST.
        
        Returns:
            Список правил парсинга
        """
        pass
    
    @abstractmethod
    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Returns:
            Список правил обработки
        """
        pass
    
    def register_resolvers(self) -> List[ResolverRule]:
        """
        Регистрирует резолверы узлов AST.
        
        Returns:
            Список правил резолвинга
        """
        return []

    def initialize(self) -> None:
        """
        Инициализирует плагин после регистрации всех компонентов.
        
        Вызывается после того, как все плагины зарегистрировали свои компоненты.
        Может использоваться для установки зависимостей между плагинами.
        """
        pass


# Типы для удобства использования
PluginList = List[TemplatePlugin]

__all__ = [
    "TemplatePlugin",
    "PluginList"
]