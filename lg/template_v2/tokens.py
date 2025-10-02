"""
Лексические типы для модульного шаблонизатора v2.

Определяет базовые типы токенов и ошибок лексического анализа.
Конкретные типы токенов регистрируются плагинами.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class TokenType(enum.Enum):
    """Базовые типы токенов в шаблоне."""
    
    # Текстовый контент
    TEXT = "TEXT"
    
    # Разделители плейсхолдеров
    PLACEHOLDER_START = "PLACEHOLDER_START"  # ${
    PLACEHOLDER_END = "PLACEHOLDER_END"      # }
    
    # Разделители директив
    DIRECTIVE_START = "DIRECTIVE_START"      # {%
    DIRECTIVE_END = "DIRECTIVE_END"          # %}
    
    # Разделители комментариев
    COMMENT_START = "COMMENT_START"          # {#
    COMMENT_END = "COMMENT_END"              # #}
    
    # Идентификаторы и ключевые слова
    IDENTIFIER = "IDENTIFIER"
    COLON = "COLON"                          # :
    AT = "AT"                                # @
    COMMA = "COMMA"                          # ,
    
    # Логические операторы
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Ключевые слова директив
    IF = "IF"
    ELIF = "ELIF"
    ELSE = "ELSE"
    ENDIF = "ENDIF"
    MODE = "MODE"
    ENDMODE = "ENDMODE"
    
    # Специальные токены
    WHITESPACE = "WHITESPACE"
    NEWLINE = "NEWLINE"
    EOF = "EOF"
    
    # Скобки для группировки в условиях
    LPAREN = "LPAREN"                        # (
    RPAREN = "RPAREN"                        # )
    
    # Квадратные скобки для адресации
    LBRACKET = "LBRACKET"                    # [
    RBRACKET = "RBRACKET"                    # ]
    
    # Якорные ссылки для md-плейсхолдеров
    HASH = "HASH"                            # #


@dataclass(frozen=True)
class Token:
    """
    Токен с позиционной информацией для точной диагностики ошибок.
    """
    type: TokenType
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


__all__ = ["TokenType", "Token", "LexerError", "ParserError"]