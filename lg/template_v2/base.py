"""
Базовые интерфейсы и абстракции для модульного шаблонизатора.

Определяет базовые классы и интерфейсы, которые должны реализовывать
плагины для интеграции в систему шаблонизации.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .protocols import TemplateRegistryProtocol
from .handlers import TemplateProcessorHandlers
# Импортируем собственные типы
from .types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ResolverRule


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
    def priority(self) -> PluginPriority:
        """Возвращает приоритет плагина (по умолчанию средний)."""
        return PluginPriority.PLACEHOLDER
    
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
            
        Raises:
            RuntimeError: Если обработчики не установлены
        """
        if self._handlers is None:
            raise RuntimeError(f"Handlers not set for plugin '{self.name}'")
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
            
        Raises:
            RuntimeError: Если реестр не установлен
        """
        if self._registry is None:
            raise RuntimeError(f"Registry not set for plugin '{self.name}'")
        return self._registry
    
    def register_tokens(self) -> List[TokenSpec]:
        """
        Регистрирует токены, которые должен распознавать лексер.
        
        Returns:
            Список спецификаций токенов
        """
        return []

    def register_token_contexts(self) -> List[Dict]:
        """
        Регистрирует контекстные группы токенов.

        Returns:
            Список описаний контекстов в формате словарей
        """
        return []

    def register_parser_rules(self) -> List[ParsingRule]:
        """
        Регистрирует правила парсинга для создания узлов AST.
        
        Returns:
            Список правил парсинга
        """
        return []
    
    def register_processors(self) -> List[ProcessorRule]:
        """
        Регистрирует обработчики узлов AST.
        
        Returns:
            Список правил обработки
        """
        return []
    
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