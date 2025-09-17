"""
Лексический анализатор для движка шаблонизации LG V2.

Токенизирует исходный текст шаблона, разбивая его на последовательность
токенов для последующего синтаксического анализа.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import List


class TokenType(enum.Enum):
    """Типы токенов в шаблоне."""
    
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
    
    # Логические операторы
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Ключевые слова директив
    IF = "IF"
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


class TemplateLexer:
    """
    Лексический анализатор шаблонов.
    
    Разбивает исходный текст на токены, учитывая различные контексты:
    - обычный текст
    - внутри плейсхолдеров ${...}
    - внутри директив {% ... %}
    - внутри комментариев {# ... #}
    """
    
    # Регулярные выражения для различных типов токенов
    _PATTERNS = {
        # Основные разделители (должны проверяться первыми)
        TokenType.PLACEHOLDER_START: re.compile(r'\$\{'),
        TokenType.DIRECTIVE_START: re.compile(r'\{%'),
        TokenType.COMMENT_START: re.compile(r'\{#'),
        TokenType.PLACEHOLDER_END: re.compile(r'\}'),
        TokenType.DIRECTIVE_END: re.compile(r'%\}'),
        TokenType.COMMENT_END: re.compile(r'#\}'),
        
        # Операторы и символы
        TokenType.COLON: re.compile(r':'),
        TokenType.AT: re.compile(r'@'),
        TokenType.LPAREN: re.compile(r'\('),
        TokenType.RPAREN: re.compile(r'\)'),
        TokenType.LBRACKET: re.compile(r'\['),
        TokenType.RBRACKET: re.compile(r'\]'),
        
        # Пробельные символы
        TokenType.NEWLINE: re.compile(r'\r?\n'),
        TokenType.WHITESPACE: re.compile(r'[ \t]+'),
        
        # Идентификаторы (буквы, цифры, подчёркивание, дефис, слеш, точка)
        TokenType.IDENTIFIER: re.compile(r'[A-Za-z0-9_\-/.]+'),
    }
    
    # Ключевые слова
    _KEYWORDS = {
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'endif': TokenType.ENDIF,
        'mode': TokenType.MODE,
        'endmode': TokenType.ENDMODE,
        'AND': TokenType.AND,
        'OR': TokenType.OR,
        'NOT': TokenType.NOT,
    }
    
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        
    def tokenize(self) -> List[Token]:
        """
        Токенизирует весь исходный текст и возвращает список токенов.
        """
        tokens: List[Token] = []
        
        while self.position < self.length:
            token = self.next_token()
            if token.type != TokenType.EOF:
                tokens.append(token)
            else:
                break
        
        # Добавляем EOF токен
        tokens.append(Token(TokenType.EOF, "", self.position, self.line, self.column))
        
        return tokens
    
    def next_token(self) -> Token:
        """
        Извлекает следующий токен из входного потока.
        """
        if self.position >= self.length:
            return Token(TokenType.EOF, "", self.position, self.line, self.column)
        
        # Сохраняем текущую позицию для токена
        start_pos = self.position
        start_line = self.line
        start_column = self.column
        
        # Проверяем специальные разделители первыми
        for token_type in [
            TokenType.PLACEHOLDER_START,
            TokenType.DIRECTIVE_START, 
            TokenType.COMMENT_START,
            TokenType.PLACEHOLDER_END,
            TokenType.DIRECTIVE_END,
            TokenType.COMMENT_END,
        ]:
            pattern = self._PATTERNS[token_type]
            match = pattern.match(self.text, self.position)
            if match:
                value = match.group(0)
                self._advance(len(value))
                return Token(token_type, value, start_pos, start_line, start_column)
        
        # Если не нашли специальных разделителей, считаем это текстом
        # Читаем до следующего специального символа или конца
        text_end = self._find_next_special_sequence()
        if text_end > self.position:
            value = self.text[self.position:text_end]
            self._advance(len(value))
            return Token(TokenType.TEXT, value, start_pos, start_line, start_column)
        
        # Неожиданный символ
        char = self.text[self.position]
        raise LexerError(
            f"Unexpected character: {char!r}",
            self.line, self.column, self.position
        )
    
    def _advance(self, count: int) -> None:
        """
        Перемещает позицию на указанное количество символов,
        обновляя номера строк и колонок.
        """
        for _ in range(count):
            if self.position < self.length:
                if self.text[self.position] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.position += 1
    
    def _find_next_special_sequence(self) -> int:
        """
        Находит позицию следующей специальной последовательности
        (${, {%, {#, }, %}, #}) или конец текста.
        """
        pos = self.position
        while pos < self.length:
            char = self.text[pos]
            
            # Открывающие последовательности
            if char == '$' and pos + 1 < self.length and self.text[pos + 1] == '{':
                return pos  # Найден ${
            elif char == '{' and pos + 1 < self.length:
                next_char = self.text[pos + 1]
                if next_char in '%#':
                    return pos  # Найден {% или {#
                    
            # Закрывающие последовательности  
            elif char == '}':
                return pos  # Найден }
            elif char == '%' and pos + 1 < self.length and self.text[pos + 1] == '}':
                return pos  # Найден %}  
            elif char == '#' and pos + 1 < self.length and self.text[pos + 1] == '}':
                return pos  # Найден #}
            
            pos += 1
        return self.length
    
    def tokenize_placeholder_content(self, content: str) -> List[Token]:
        """
        Токенизирует содержимое плейсхолдера ${...}.
        
        Используется для обработки содержимого между ${ и }.
        """
        # Создаем временный лексер для содержимого
        temp_lexer = TemplateLexer(content)
        tokens = []
        
        while temp_lexer.position < temp_lexer.length:
            token = temp_lexer._tokenize_inside_placeholder()
            if token.type == TokenType.EOF:
                break
            tokens.append(token)
        
        return tokens
    
    def tokenize_directive_content(self, content: str) -> List[Token]:
        """
        Токенизирует содержимое директивы {% ... %}.
        
        Используется для обработки содержимого между {% и %}.
        """
        # Создаем временный лексер для содержимого
        temp_lexer = TemplateLexer(content)
        tokens = []
        
        while temp_lexer.position < temp_lexer.length:
            token = temp_lexer._tokenize_inside_directive()
            if token.type == TokenType.EOF:
                break
            tokens.append(token)
        
        return tokens
    
    def _tokenize_inside_placeholder(self) -> Token:
        """Токенизирует содержимое внутри плейсхолдера."""
        if self.position >= self.length:
            return Token(TokenType.EOF, "", self.position, self.line, self.column)
        
        start_pos = self.position
        start_line = self.line
        start_column = self.column
        
        # Пропускаем пробелы
        if self._PATTERNS[TokenType.WHITESPACE].match(self.text, self.position):
            match = self._PATTERNS[TokenType.WHITESPACE].match(self.text, self.position)
            if match:
                self._advance(len(match.group(0)))
                return self._tokenize_inside_placeholder()  # Рекурсивно продолжаем
        
        # Проверяем специальные символы
        for token_type in [TokenType.COLON, TokenType.AT, TokenType.LBRACKET, TokenType.RBRACKET]:
            pattern = self._PATTERNS[token_type]
            match = pattern.match(self.text, self.position)
            if match:
                value = match.group(0)
                self._advance(len(value))
                return Token(token_type, value, start_pos, start_line, start_column)
        
        # Проверяем идентификаторы
        pattern = self._PATTERNS[TokenType.IDENTIFIER]
        match = pattern.match(self.text, self.position)
        if match:
            value = match.group(0)
            self._advance(len(value))
            return Token(TokenType.IDENTIFIER, value, start_pos, start_line, start_column)
        
        # Неожиданный символ
        char = self.text[self.position]
        raise LexerError(
            f"Unexpected character in placeholder: {char!r}",
            self.line, self.column, self.position
        )
    
    def _tokenize_inside_directive(self) -> Token:
        """Токенизирует содержимое внутри директивы."""
        if self.position >= self.length:
            return Token(TokenType.EOF, "", self.position, self.line, self.column)
        
        start_pos = self.position
        start_line = self.line
        start_column = self.column
        
        # Пропускаем пробелы
        whitespace_match = self._PATTERNS[TokenType.WHITESPACE].match(self.text, self.position)
        if whitespace_match:
            self._advance(len(whitespace_match.group(0)))
            return self._tokenize_inside_directive()  # Рекурсивно продолжаем
        
        # Проверяем специальные символы
        for token_type in [TokenType.COLON, TokenType.LPAREN, TokenType.RPAREN]:
            pattern = self._PATTERNS[token_type]
            match = pattern.match(self.text, self.position)
            if match:
                value = match.group(0)
                self._advance(len(value))
                return Token(token_type, value, start_pos, start_line, start_column)
        
        # Проверяем идентификаторы и ключевые слова
        pattern = self._PATTERNS[TokenType.IDENTIFIER]
        match = pattern.match(self.text, self.position)
        if match:
            value = match.group(0)
            self._advance(len(value))
            
            # Проверяем ключевые слова
            keyword_type = self._KEYWORDS.get(value)
            if keyword_type:
                return Token(keyword_type, value, start_pos, start_line, start_column)
            
            return Token(TokenType.IDENTIFIER, value, start_pos, start_line, start_column)
        
        # Неожиданный символ
        char = self.text[self.position]
        raise LexerError(
            f"Unexpected character in directive: {char!r}",
            self.line, self.column, self.position
        )


def tokenize_template(text: str) -> List[Token]:
    """
    Удобная функция для токенизации шаблона.
    
    Args:
        text: Исходный текст шаблона
        
    Returns:
        Список токенов
        
    Raises:
        LexerError: При ошибке лексического анализа
    """
    lexer = TemplateLexer(text)
    return lexer.tokenize()