from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from re import Pattern
from typing import Callable, Optional, Type, List, Dict
from typing import Set

from .nodes import TemplateNode
from .tokens import Token, TokenType, TokenTypeName, ParserError


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
    priority: int = 50           # Приоритет (больше = проверяется раньше)


@dataclass
class ParsingRule:
    """
    Правило парсинга для регистрации в парсере.
    """
    name: str                    # Имя правила
    priority: int     # Приоритет применения
    parser_func: Callable[[ParsingContext], Optional[TemplateNode]]  # Функция парсинга
    enabled: bool = True        # Включено ли правило


@dataclass
class ProcessingContext:
    """
    Контекст обработки узла AST.
    
    Предоставляет плагинам доступ к состоянию обработки без нарушения инкапсуляции.
    """
    ast: List[TemplateNode]  # Текущий AST
    node_index: int          # Индекс обрабатываемого узла
    
    def get_node(self) -> TemplateNode:
        """Возвращает текущий обрабатываемый узел."""
        return self.ast[self.node_index]


@dataclass
class ProcessorRule:
    """
    Правило обработки узлов AST.
    """
    node_type: Type[TemplateNode]  # Тип узла, который обрабатывает правило
    processor_func: Callable[[ProcessingContext], str]  # Функция обработки (node, context)


@dataclass
class ResolverRule:
    """
    Правило резолвинга узлов AST.
    """
    node_type: Type[TemplateNode]  # Тип узла, который резолвит правило
    resolver_func: Callable[[TemplateNode, str], TemplateNode]  # Функция резолвинга (node, context) -> resolved_node


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
            return Token(TokenType.EOF.value, "", self.position, 0, 0)
        return self.tokens[self.position]

    def peek(self, offset: int = 1) -> Token:
        """Возвращает токен на указанном смещении от текущей позиции."""
        pos = self.position + offset
        if pos >= self.length:
            return Token(TokenType.EOF.value, "", pos, 0, 0)
        return self.tokens[pos]

    def advance(self) -> Token:
        """Продвигается к следующему токену и возвращает предыдущий."""
        current = self.current()
        if self.position < self.length:
            self.position += 1
        return current

    def is_at_end(self) -> bool:
        """Проверяет, достигнут ли конец токенов."""
        return self.position >= self.length or self.current().type == TokenType.EOF.value

    def match(self, *token_types: TokenTypeName) -> bool:
        """Проверяет, соответствует ли текущий токен одному из указанных типов."""
        return self.current().type in token_types

    def consume(self, expected_type: TokenTypeName) -> Token:
        """
        Потребляет токен ожидаемого типа.

        Raises:
            ParserError: Если токен не соответствует ожидаемому типу
        """
        current = self.current()
        if current.type != expected_type:
            raise ParserError(
                f"Expected {expected_type}, got {current.type}",
                current
            )
        return self.advance()


logger = logging.getLogger(__name__)

@dataclass
class TokenContext:
    """
    Контекст для токенизации с группами связанных токенов.

    Определяет область действия определенного набора токенов,
    что позволяет избежать коллизий и повысить производительность.
    """
    name: str  # Уникальное имя контекста
    open_tokens: Set[str]  # Токены, открывающие контекст
    close_tokens: Set[str]  # Токены, закрывающие контекст
    inner_tokens: Set[str]  # Токены, допустимые только в этом контексте
    allow_nesting: bool = False  # Разрешает/запрещает вложенные контексты
    priority: int = 50  # Приоритет (для разрешения конфликтов)

    def __post_init__(self):
        """Валидация настроек контекста."""
        if not self.name:
            raise ValueError("Token context name cannot be empty")

        if not self.open_tokens and not self.close_tokens:
            raise ValueError(f"Context '{self.name}' must have at least open or close tokens")

        # Проверяем пересечения между наборами токенов
        if self.open_tokens & self.close_tokens:
            overlapping = self.open_tokens & self.close_tokens
            logger.warning(
                f"Context '{self.name}' has overlapping open/close tokens: {overlapping}"
            )


TokenRegistry = Dict[str, TokenSpec]
ParserRulesRegistry = Dict[str, ParsingRule]
ProcessorRegistry = Dict[Type[TemplateNode], List[ProcessorRule]]
ResolverRegistry = Dict[Type[TemplateNode], List[ResolverRule]]


__all__ = [
    "PluginPriority",
    "TokenSpec",
    "ParsingRule",
    "ProcessingContext",
    "ProcessorRule",
    "ResolverRule",
    "ParsingContext",
    "TokenContext",
    "TokenRegistry",
    "ParserRulesRegistry",
    "ProcessorRegistry",
    "ResolverRegistry",
]
