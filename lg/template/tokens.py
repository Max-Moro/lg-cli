"""
Лексические типы.

Определяет базовые типы токенов.
Конкретные типы токенов регистрируются плагинами.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class TokenType(enum.Enum):
    """Базовые типы токенов в шаблоне. Плагины регистрируют свои токены через TokenRegistry."""
    TEXT = "TEXT"
    EOF = "EOF"


# Упрощенная система токенов - используем строки напрямую
TokenTypeName = str


@dataclass(frozen=True)
class Token:
    """
    Токен с позиционной информацией для точной диагностики ошибок.
    """
    type: TokenTypeName
    value: str
    position: int        # Позиция в исходном тексте
    line: int           # Номер строки (начиная с 1)
    column: int         # Номер колонки (начиная с 1)
    
    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, {self.line}:{self.column})"


class ParserError(Exception):
    """Ошибка синтаксического анализа."""
    
    def __init__(self, message: str, token: Token):
        super().__init__(f"{message} at {token.line}:{token.column} (token: {token.type})")
        self.token = token
        self.line = token.line
        self.column = token.column


__all__ = [
    "TokenType", 
    "TokenTypeName",
    "Token", 
    "ParserError"
]