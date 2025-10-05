"""
Лексический анализатор для HTML-комментариев с LG-инструкциями.

Обнаруживает и извлекает специальные HTML-комментарии, содержащие
условную логику для Markdown-адаптера.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class CommentToken:
    """
    Токен HTML-комментария с LG-инструкцией.
    
    Представляет специальный комментарий с указанием его типа и содержимого.
    """
    type: str  # 'if', 'elif', 'else', 'endif', 'comment:start', 'comment:end'
    content: str  # Содержимое комментария (например, условие для if/elif)
    start_pos: int  # Позиция начала в исходном тексте
    end_pos: int   # Позиция конца в исходном тексте
    full_match: str  # Полный текст комментария


class MarkdownTemplateLexer:
    """
    Лексер для поиска и извлечения LG-инструкций из HTML-комментариев в Markdown.
    
    Распознает следующие конструкции:
    - <!-- lg:if condition --> 
    - <!-- lg:elif condition -->
    - <!-- lg:else -->
    - <!-- lg:endif -->
    - <!-- lg:comment:start -->
    - <!-- lg:comment:end -->
    - <!-- lg:raw:start -->
    - <!-- lg:raw:end -->
    """
    
    # Регулярное выражение для поиска LG-комментариев
    LG_COMMENT_PATTERN = re.compile(
        r'<!--\s*lg:([a-z:]+)(?:\s+([^-]+(?:-(?!->)[^-]*)*))?\s*-->',
        re.MULTILINE
    )
    
    def __init__(self, text: str):
        """
        Инициализирует лексер с исходным текстом.
        
        Args:
            text: Исходный Markdown-текст для анализа
        """
        self.text = text
        self.length = len(text)
    
    def tokenize(self) -> List[CommentToken]:
        """
        Извлекает все LG-комментарии из текста.
        
        Returns:
            Список токенов комментариев, отсортированный по позиции в тексте
        """
        tokens = []
        
        for match in self.LG_COMMENT_PATTERN.finditer(self.text):
            token_type = match.group(1)  # Тип инструкции (if, elif, else, etc.)
            content = match.group(2) or ""  # Содержимое (условие для if/elif)
            start_pos = match.start()
            end_pos = match.end()
            full_match = match.group(0)
            
            # Очищаем содержимое от лишних пробелов
            content = content.strip()
            
            # Валидируем тип токена
            if not self._is_valid_token_type(token_type):
                # Игнорируем неизвестные типы комментариев
                continue
            
            token = CommentToken(
                type=token_type,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos,
                full_match=full_match
            )
            
            tokens.append(token)
        
        # Сортируем токены по позиции в тексте
        tokens.sort(key=lambda t: t.start_pos)
        
        return tokens
    
    def find_text_segments(self, tokens: List[CommentToken]) -> List[Tuple[int, int, str]]:
        """
        Разбивает текст на сегменты между LG-комментариями.
        
        Args:
            tokens: Список токенов комментариев
            
        Returns:
            Список кортежей (start_pos, end_pos, segment_type),
            где segment_type может быть 'text' или 'comment'
        """
        segments = []
        current_pos = 0
        
        for token in tokens:
            # Добавляем текстовый сегмент перед комментарием
            if current_pos < token.start_pos:
                segments.append((current_pos, token.start_pos, 'text'))
            
            # Добавляем сам комментарий
            segments.append((token.start_pos, token.end_pos, 'comment'))
            
            current_pos = token.end_pos
        
        # Добавляем оставшийся текст после последнего комментария
        if current_pos < self.length:
            segments.append((current_pos, self.length, 'text'))
        
        return segments
    
    def extract_text_between(self, start_token: CommentToken, end_token: CommentToken) -> str:
        """
        Извлекает текст между двумя токенами комментариев.
        
        Args:
            start_token: Начальный токен (например, lg:if)
            end_token: Конечный токен (например, lg:endif)
            
        Returns:
            Текст между токенами
        """
        if start_token.end_pos >= end_token.start_pos:
            return ""
        
        return self.text[start_token.end_pos:end_token.start_pos]
    
    def _is_valid_token_type(self, token_type: str) -> bool:
        """
        Проверяет, является ли тип токена валидным.
        
        Args:
            token_type: Тип токена для проверки
            
        Returns:
            True если тип токена поддерживается
        """
        valid_types = {
            'if',
            'elif', 
            'else',
            'endif',
            'comment:start',
            'comment:end',
            'raw:start',
            'raw:end'
        }
        
        return token_type in valid_types
    
    def validate_tokens(self, tokens: List[CommentToken]) -> List[str]:
        """
        Валидирует последовательность токенов на корректность структуры.
        
        Args:
            tokens: Список токенов для валидации
            
        Returns:
            Список ошибок валидации (пустой если ошибок нет)
        """
        errors = []
        stack = []  # Стек для отслеживания открытых блоков
        comment_blocks = 0  # Счетчик открытых comment блоков
        
        for i, token in enumerate(tokens):
            if token.type == 'if':
                if not token.content:
                    errors.append(f"Token {i}: 'if' без условия на позиции {token.start_pos}")
                stack.append(('if', i))
            
            elif token.type == 'elif':
                if not token.content:
                    errors.append(f"Token {i}: 'elif' без условия на позиции {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif'):
                    errors.append(f"Token {i}: 'elif' без соответствующего 'if' на позиции {token.start_pos}")
                else:
                    # Заменяем последний элемент стека на elif
                    stack[-1] = ('elif', i)
            
            elif token.type == 'else':
                if token.content:
                    errors.append(f"Token {i}: 'else' не должен иметь условия на позиции {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif'):
                    errors.append(f"Token {i}: 'else' без соответствующего 'if' на позиции {token.start_pos}")
                else:
                    # Заменяем последний элемент стека на else
                    stack[-1] = ('else', i)
            
            elif token.type == 'endif':
                if token.content:
                    errors.append(f"Token {i}: 'endif' не должен иметь условия на позиции {token.start_pos}")
                if not stack or stack[-1][0] not in ('if', 'elif', 'else'):
                    errors.append(f"Token {i}: 'endif' без соответствующего 'if' на позиции {token.start_pos}")
                else:
                    stack.pop()
            
            elif token.type == 'comment:start':
                if token.content:
                    errors.append(f"Token {i}: 'comment:start' не должен иметь содержимого на позиции {token.start_pos}")
                comment_blocks += 1
            
            elif token.type == 'comment:end':
                if token.content:
                    errors.append(f"Token {i}: 'comment:end' не должен иметь содержимого на позиции {token.start_pos}")
                comment_blocks -= 1
                if comment_blocks < 0:
                    errors.append(f"Token {i}: 'comment:end' без соответствующего 'comment:start' на позиции {token.start_pos}")
            
            elif token.type == 'raw:start':
                if token.content:
                    errors.append(f"Token {i}: 'raw:start' не должен иметь содержимого на позиции {token.start_pos}")
                stack.append(('raw', i))
            
            elif token.type == 'raw:end':
                if token.content:
                    errors.append(f"Token {i}: 'raw:end' не должен иметь содержимого на позиции {token.start_pos}")
                if not stack or stack[-1][0] != 'raw':
                    errors.append(f"Token {i}: 'raw:end' без соответствующего 'raw:start' на позиции {token.start_pos}")
                else:
                    stack.pop()
        
        # Проверяем оставшиеся открытые блоки
        for block_type, token_index in stack:
            errors.append(f"Token {token_index}: Незакрытый блок '{block_type}'")
        
        if comment_blocks > 0:
            errors.append(f"Незакрытых 'comment' блоков: {comment_blocks}")
        
        return errors


def tokenize_markdown_template(text: str) -> List[CommentToken]:
    """
    Удобная функция для токенизации Markdown с LG-комментариями.
    
    Args:
        text: Исходный Markdown-текст
        
    Returns:
        Список токенов комментариев
    """
    lexer = MarkdownTemplateLexer(text)
    return lexer.tokenize()


__all__ = [
    "CommentToken",
    "MarkdownTemplateLexer", 
    "tokenize_markdown_template"
]