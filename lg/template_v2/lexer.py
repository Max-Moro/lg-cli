"""
Упрощенный лексический анализатор для шаблонизатора.

Выполняет базовую токенизацию шаблонов, выделяя текст и основные конструкции.
"""

from __future__ import annotations

from typing import List

from .registry import TemplateRegistry
from .tokens import Token, TokenType, LexerError


class ModularLexer:
    """
    Упрощенный лексический анализатор для базовой токенизации шаблонов.
    """
    
    def __init__(self, registry: TemplateRegistry):
        """Инициализирует лексер."""
        self.registry = registry
        
        # Позиционная информация
        self.text = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = 0

    def tokenize(self, text: str) -> List[Token]:
        """
        Простая токенизация шаблонного текста.
        
        Разделяет текст на следующие типы токенов:
        - ${...} плейсхолдеры
        - Обычный текст между плейсхолдерами
        
        Args:
            text: Исходный текст для токенизации
            
        Returns:
            Список токенов
        """
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        
        tokens: List[Token] = []
        
        while self.position < self.length:
            # Ищем начало плейсхолдера
            placeholder_start = self.text.find('${', self.position)
            
            if placeholder_start == -1:
                # Больше плейсхолдеров нет, весь оставшийся текст - это TEXT
                if self.position < self.length:
                    text_content = self.text[self.position:]
                    start_line, start_column = self.line, self.column
                    self._advance(len(text_content))
                    tokens.append(Token(
                        TokenType.TEXT.value, text_content, 
                        self.position - len(text_content), start_line, start_column
                    ))
                break
            
            # Добавляем текст до плейсхолдера
            if placeholder_start > self.position:
                text_content = self.text[self.position:placeholder_start]
                start_line, start_column = self.line, self.column
                self._advance(len(text_content))
                tokens.append(Token(
                    TokenType.TEXT.value, text_content,
                    placeholder_start - len(text_content), start_line, start_column
                ))
            
            # Обрабатываем плейсхолдер
            placeholder_tokens = self._tokenize_placeholder()
            tokens.extend(placeholder_tokens)
        
        # Добавляем EOF токен
        tokens.append(Token(TokenType.EOF.value, "", self.position, self.line, self.column))
        
        return tokens
    
    def _tokenize_placeholder(self) -> List[Token]:
        """Токенизирует плейсхолдер ${...}."""
        tokens = []
        start_line, start_column = self.line, self.column
        
        # ${
        tokens.append(Token("PLACEHOLDER_START", "${", self.position, start_line, start_column))
        self._advance(2)
        
        # Ищем конец плейсхолдера
        end_pos = self.text.find('}', self.position)
        if end_pos == -1:
            raise LexerError(
                "Unclosed placeholder",
                self.line, self.column, self.position
            )
        
        # Содержимое плейсхолдера
        content = self.text[self.position:end_pos].strip()
        if content:
            content_tokens = self._tokenize_placeholder_content(content)
            tokens.extend(content_tokens)
        
        # Перемещаемся к закрывающей скобке
        self._advance(end_pos - self.position)
        
        # }
        tokens.append(Token("PLACEHOLDER_END", "}", self.position, self.line, self.column))
        self._advance(1)
        
        return tokens
    
    def _tokenize_placeholder_content(self, content: str) -> List[Token]:
        """Простая токенизация содержимого плейсхолдера."""
        tokens = []
        pos = 0
        
        while pos < len(content):
            # Пропускаем пробелы
            while pos < len(content) and content[pos].isspace():
                pos += 1
            
            if pos >= len(content):
                break
            
            # Специальные символы
            if content[pos] in ':@[]':
                tokens.append(Token(
                    self._get_special_token_type(content[pos]),
                    content[pos], 
                    self.position + pos, self.line, self.column
                ))
                pos += 1
            else:
                # Идентификатор
                start_pos = pos
                while (pos < len(content) and 
                       (content[pos].isalnum() or content[pos] in '_-/.') and
                       content[pos] not in ':@[]'):
                    pos += 1
                
                if pos > start_pos:
                    identifier = content[start_pos:pos]
                    tokens.append(Token(
                        "IDENTIFIER", identifier,
                        self.position + start_pos, self.line, self.column
                    ))
        
        return tokens
    
    def _get_special_token_type(self, char: str) -> str:
        """Возвращает тип токена для специального символа."""
        mapping = {
            ':': 'COLON',
            '@': 'AT', 
            '[': 'LBRACKET',
            ']': 'RBRACKET'
        }
        return mapping.get(char, 'UNKNOWN')
    
    def _advance(self, count: int) -> None:
        """Перемещает позицию на указанное количество символов."""
        for _ in range(count):
            if self.position >= self.length:
                break
                
            char = self.text[self.position]
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            
            self.position += 1


__all__ = ["ModularLexer"]