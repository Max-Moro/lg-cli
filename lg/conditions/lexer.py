"""
Лексер для разбора условных выражений.

Выполняет токенизацию строки условия, разбивая её на значимые элементы:
- Ключевые слова (tag, TAGSET, scope, AND, OR, NOT)
- Идентификаторы (имена тегов, наборов и скоупов)
- Символы (скобки, двоеточия)
- Пробелы (игнорируются)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Iterator


@dataclass
class Token:
    """
    Токен для парсинга условий.
    
    Attributes:
        type: Тип токена (KEYWORD, IDENTIFIER, SYMBOL, EOF)
        value: Значение токена
        position: Позиция в исходной строке
    """
    type: str
    value: str
    position: int
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', pos={self.position})"


class ConditionLexer:
    """
    Лексер для разбиения строки условия на токены.
    
    Поддерживаемые токены:
    - KEYWORD: tag, TAGSET, scope, AND, OR, NOT
    - IDENTIFIER: имена тегов, наборов, скоупов
    - SYMBOL: (, ), :
    - EOF: конец строки
    """
    
    # Спецификация токенов: (regex_pattern, token_type, ignore_flag)
    TOKEN_SPECS = [
        # Пробелы и табуляция (игнорируем)
        (r'\s+', 'WHITESPACE', True),
        
        # Символы (проверяем перед идентификаторами)
        (r'\(', 'SYMBOL', False),
        (r'\)', 'SYMBOL', False),
        (r':', 'SYMBOL', False),
        
        # Идентификаторы (Unicode буквы, цифры, подчёркивания, дефисы)
        # Ключевые слова будем определять после захвата
        (r'[\w][\w-]*', 'IDENTIFIER', False),
        
        # Неизвестный символ (ошибка)
        (r'.', 'UNKNOWN', False),
    ]
    
    # Ключевые слова для постпроцессинга
    KEYWORDS = {
        'TAGSET', 'scope', 'tag', 'task', 'AND', 'OR', 'NOT'
    }
    
    def __init__(self):
        # Компилируем регулярные выражения для лучшей производительности
        self._compiled_patterns = [
            (re.compile(pattern), token_type, ignore)
            for pattern, token_type, ignore in self.TOKEN_SPECS
        ]
    
    def tokenize(self, text: str) -> List[Token]:
        """
        Разбивает строку на токены.
        
        Args:
            text: Строка условия для разбора
            
        Returns:
            Список токенов, включая EOF в конце
            
        Raises:
            ValueError: При обнаружении неизвестного символа
        """
        tokens: List[Token] = []
        position = 0
        
        while position < len(text):
            match_found = False
            
            for pattern, token_type, ignore in self._compiled_patterns:
                match = pattern.match(text, position)
                if match:
                    value = match.group(0)
                    
                    if not ignore:
                        if token_type == 'UNKNOWN':
                            raise ValueError(f"Unexpected character '{value}' at position {position}")
                        
                        # Определяем тип токена: ключевое слово или идентификатор
                        final_type = token_type
                        if token_type == 'IDENTIFIER' and value in self.KEYWORDS:
                            final_type = 'KEYWORD'
                        
                        tokens.append(Token(
                            type=final_type,
                            value=value,
                            position=position
                        ))
                    
                    position = match.end()
                    match_found = True
                    break
            
            if not match_found:
                # Это не должно происходить, так как у нас есть паттерн для любого символа
                raise ValueError(f"Failed to tokenize at position {position}")
        
        # Добавляем EOF токен
        tokens.append(Token(type='EOF', value='', position=position))
        
        return tokens
    
    def tokenize_stream(self, text: str) -> Iterator[Token]:
        """
        Генератор для ленивой токенизации.
        
        Args:
            text: Строка условия для разбора
            
        Yields:
            Token: Очередной токен
        """
        for token in self.tokenize(text):
            yield token