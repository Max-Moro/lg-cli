"""
Лексические типы для модульного шаблонизатора v2.

Определяет базовые типы токенов и ошибок лексического анализа.
Конкретные типы токенов регистрируются плагинами.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Dict, Union, Optional


class TokenType(enum.Enum):
    """Базовые типы токенов в шаблоне. Плагины регистрируют свои токены через TokenRegistry."""
    
    # Базовый текстовый контент
    TEXT = "TEXT"
    
    # Базовые идентификаторы и разделители
    IDENTIFIER = "IDENTIFIER"
    COLON = "COLON"                          # :
    AT = "AT"                                # @
    COMMA = "COMMA"                          # ,
    
    # Базовые скобки (используются в разных плагинах)
    LPAREN = "LPAREN"                        # (
    RPAREN = "RPAREN"                        # )
    LBRACKET = "LBRACKET"                    # [
    RBRACKET = "RBRACKET"                    # ]
    
    # Служебные токены
    WHITESPACE = "WHITESPACE"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


class DynamicTokenType:
    """
    Расширяемый тип токена, который может быть как базовым TokenType, так и динамически зарегистрированным.
    
    Используется лексером и парсером для работы с токенами плагинов.
    """
    
    def __init__(self, value: Union[TokenType, str]):
        if isinstance(value, TokenType):
            self._value = value.value
            self._is_base = True
        else:
            self._value = str(value)
            self._is_base = False
    
    @property
    def name(self) -> str:
        """Возвращает имя токена."""
        return self._value
    
    @property
    def is_base(self) -> bool:
        """Возвращает True если это базовый токен из TokenType enum."""
        return self._is_base
    
    def __str__(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        prefix = "TokenType" if self._is_base else "DynamicToken"
        return f"{prefix}({self._value})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, DynamicTokenType):
            return self._value == other._value
        elif isinstance(other, TokenType):
            return self._is_base and self._value == other.value
        elif isinstance(other, str):
            return self._value == other
        return False
    
    def __hash__(self) -> int:
        return hash(self._value)


class TokenRegistry:
    """
    Реестр для динамической регистрации токенов плагинами.
    
    Позволяет плагинам регистрировать собственные токены без изменения базового TokenType enum.
    """
    
    def __init__(self):
        self._dynamic_tokens: Dict[str, DynamicTokenType] = {}
        
        # Предрегистрируем базовые токены
        for base_token in TokenType:
            self._dynamic_tokens[base_token.value] = DynamicTokenType(base_token)
    
    def register_token(self, name: str) -> DynamicTokenType:
        """
        Регистрирует новый динамический токен.
        
        Args:
            name: Имя токена
            
        Returns:
            DynamicTokenType для использования в плагине
        """
        if name not in self._dynamic_tokens:
            self._dynamic_tokens[name] = DynamicTokenType(name)
        return self._dynamic_tokens[name]
    
    def get_token(self, name: str) -> Optional[DynamicTokenType]:
        """
        Получает токен по имени (базовый или динамический).
        
        Args:
            name: Имя токена
            
        Returns:
            DynamicTokenType или None если токен не найден
        """
        return self._dynamic_tokens.get(name)
    
    def get_all_tokens(self) -> Dict[str, DynamicTokenType]:
        """Возвращает все зарегистрированные токены."""
        return dict(self._dynamic_tokens)


@dataclass(frozen=True)
class Token:
    """
    Токен с позиционной информацией для точной диагностики ошибок.
    """
    type: DynamicTokenType
    value: str
    position: int        # Позиция в исходном тексте
    line: int           # Номер строки (начиная с 1)
    column: int         # Номер колонки (начиная с 1)
    
    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class LexerError(Exception):
    """Ошибка лексического анализа."""
    
    def __init__(self, message: str, line: int, column: int, position: int):
        super().__init__(f"{message} at {line}:{column}")
        self.line = line
        self.column = column
        self.position = position


class ParserError(Exception):
    """Ошибка синтаксического анализа."""
    
    def __init__(self, message: str, token: Token):
        super().__init__(f"{message} at {token.line}:{token.column} (token: {token.type.name})")
        self.token = token
        self.line = token.line
        self.column = token.column


__all__ = [
    "TokenType", 
    "DynamicTokenType", 
    "TokenRegistry",
    "Token", 
    "LexerError", 
    "ParserError"
]