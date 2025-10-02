"""
Базовые интерфейсы и абстракции для модульного шаблонизатора.

Определяет базовые классы и интерфейсы, которые должны реализовывать
плагины для интеграции в систему шаблонизации.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Pattern, Type

from .handlers import TemplateProcessorHandlers
# Импортируем собственные типы
from .nodes import TemplateNode
from .tokens import Token, TokenType, DynamicTokenType, ParserError


class PluginPriority(enum.IntEnum):
    """Приоритеты для определения порядка применения правил парсинга."""
    
    # Специальные конструкции должны обрабатываться раньше обычного текста
    DIRECTIVE = 100      # Директивы {% ... %}
    PLACEHOLDER = 90     # Плейсхолдеры ${ ... }
    COMMENT = 80        # Комментарии {# ... #}
    TEXT = 10           # Обычный текст (самый низкий приоритет)


@dataclass
class TokenSpec:
    """
    Спецификация токена для регистрации в лексере.
    """
    name: str                    # Имя токена (например, "PLACEHOLDER_START")
    pattern: Pattern[str]        # Скомпилированное регулярное выражение
    priority: int = 50          # Приоритет применения паттерна
    context_sensitive: bool = False  # Зависит ли токен от контекста


@dataclass
class ParsingRule:
    """
    Правило парсинга для регистрации в парсере.
    """
    name: str                    # Имя правила
    priority: PluginPriority     # Приоритет применения
    parser_func: Callable[[ParsingContext], Optional[TemplateNode]]  # Функция парсинга
    enabled: bool = True        # Включено ли правило


@dataclass
class ProcessorRule:
    """
    Правило обработки узлов AST.
    """
    node_type: Type[TemplateNode]  # Тип узла, который обрабатывает правило
    processor_func: Callable[[TemplateNode], str]  # Функция обработки
    priority: int = 50            # Приоритет (для случаев множественных обработчиков)


class ParsingContext:
    """
    Контекст для парсинга токенов.
    
    Предоставляет методы для навигации по токенам и управления позицией
    в процессе синтаксического анализа.
    """
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.length = len(tokens)

        # Стек для сохранения/восстановления позиции
        self._position_stack: List[int] = []

    def current(self) -> Token:
        """Возвращает текущий токен."""
        if self.position >= self.length:
            # Возвращаем EOF токен
            return Token(DynamicTokenType(TokenType.EOF), "", self.position, 0, 0)
        return self.tokens[self.position]
    
    def peek(self, offset: int = 1) -> Token:
        """Возвращает токен на указанном смещении от текущей позиции."""
        pos = self.position + offset
        if pos >= self.length:
            return Token(DynamicTokenType(TokenType.EOF), "", pos, 0, 0)
        return self.tokens[pos]
    
    def advance(self) -> Token:
        """Продвигается к следующему токену и возвращает предыдущий."""
        current = self.current()
        if self.position < self.length:
            self.position += 1
        return current
    
    def is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец токенов."""
        return self.position >= self.length or self.current().type == DynamicTokenType(TokenType.EOF)

    def save_position(self) -> None:
        """Сохраняет текущую позицию в стек."""
        self._position_stack.append(self.position)

    def restore_position(self) -> None:
        """Восстанавливает позицию из стека."""
        if self._position_stack:
            self.position = self._position_stack.pop()

    def discard_saved_position(self) -> None:
        """Удаляет сохраненную позицию без восстановления."""
        if self._position_stack:
            self._position_stack.pop()

    def match(self, *token_types: DynamicTokenType) -> bool:
        """Проверяет, соответствует ли текущий токен одному из указанных типов."""
        return self.current().type in token_types
    
    def consume(self, expected_type: DynamicTokenType) -> Token:
        """
        Потребляет токен ожидаемого типа.
        
        Raises:
            ParserError: Если токен не соответствует ожидаемому типу
        """
        current = self.current()
        if current.type != expected_type:
            raise ParserError(
                f"Expected {expected_type.name}, got {current.type.name}", 
                current
            )
        return self.advance()


class TemplatePlugin(ABC):
    """
    Базовый интерфейс для плагинов шаблонизатора.
    
    Каждый плагин должен реализовать этот интерфейс для регистрации
    своих компонентов в системе шаблонизации.
    """
    
    def __init__(self):
        """Инициализирует плагин."""
        self._handlers: Optional[TemplateProcessorHandlers] = None
    
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
    
    def register_tokens(self) -> List[TokenSpec]:
        """
        Регистрирует токены, которые должен распознавать лексер.
        
        Returns:
            Список спецификаций токенов
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
    
    def initialize(self) -> None:
        """
        Инициализирует плагин после регистрации всех компонентов.
        
        Вызывается после того, как все плагины зарегистрировали свои компоненты.
        Может использоваться для установки зависимостей между плагинами.
        """
        pass


class ProcessingError(Exception):
    """
    Базовый класс для ошибок обработки в модульном шаблонизаторе.
    
    Расширяет стандартные исключения информацией о контексте обработки.
    """
    
    def __init__(self, message: str, node: Optional[TemplateNode] = None, 
                 plugin_name: Optional[str] = None):
        super().__init__(message)
        self.node = node
        self.plugin_name = plugin_name
        
    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.plugin_name:
            parts.append(f"Plugin: {self.plugin_name}")
        if self.node:
            parts.append(f"Node: {type(self.node).__name__}")
        return " | ".join(parts)


# Типы для удобства использования
TokenRegistry = Dict[str, TokenSpec]
ParserRulesRegistry = Dict[str, ParsingRule] 
ProcessorRegistry = Dict[Type[TemplateNode], List[ProcessorRule]]
PluginList = List[TemplatePlugin]

__all__ = [
    "TemplatePlugin", 
    "ParsingContext",
    "PluginPriority",
    "TokenSpec",
    "ParsingRule", 
    "ProcessorRule",
    "ProcessingError",
    "TokenRegistry",
    "ParserRulesRegistry",
    "ProcessorRegistry",
    "PluginList"
]