"""
Модульный лексический анализатор для шаблонизатора.

Использует зарегистрированные токены из плагинов для универсальной токенизации,
поддерживая как базовые конструкции, так и специализированные токены плагинов.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .base import TokenSpec
from .registry import TemplateRegistry
from .tokens import Token, TokenType, LexerError

logger = logging.getLogger(__name__)


class ModularLexer:
    """
    Модульный лексический анализатор использующий токены из плагинов.
    
    Использует зарегистрированные в TemplateRegistry спецификации токенов
    для универсальной токенизации любых шаблонных конструкций.
    """
    
    def __init__(self, registry: TemplateRegistry):
        """
        Инициализирует лексер с реестром плагинов.
        
        Args:
            registry: Реестр с зарегистрированными токенами
        """
        self.registry = registry
        
        # Позиционная информация
        self.text = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = 0
        
        # Кэшированные спецификации токенов (обновляются при смене реестра)
        self._cached_token_specs: Optional[List[TokenSpec]] = None

    def tokenize(self, text: str) -> List[Token]:
        """
        Универсальная токенизация с использованием зарегистрированных токенов.
        
        Применяет все зарегистрированные токены в порядке приоритета,
        автоматически обрабатывая специальные конструкции плагинов.
        
        Args:
            text: Исходный текст для токенизации
            
        Returns:
            Список токенов
            
        Raises:
            LexerError: При ошибке токенизации
        """
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        
        tokens: List[Token] = []
        
        # Получаем отсортированные спецификации токенов
        token_specs = self._get_token_specs()
        
        while self.position < self.length:
            token = self._match_next_token(token_specs)
            
            if token is None:
                # Не удалось найти подходящий токен - это ошибка
                char = self.text[self.position] if self.position < self.length else 'EOF'
                raise LexerError(
                    f"Unexpected character '{char}'",
                    self.line, self.column, self.position
                )
                
            # Добавляем все токены (включая TEXT и пропуская пустые)
            if token.value:  # Пропускаем токены с пустым содержимым
                tokens.append(token)
        
        # Добавляем EOF токен
        tokens.append(Token(TokenType.EOF.value, "", self.position, self.line, self.column))
        
        logger.debug(f"Tokenized text into {len(tokens)} tokens")
        return tokens
    
    def _get_token_specs(self) -> List[TokenSpec]:
        """
        Получает отсортированные спецификации токенов из реестра.
        
        Returns:
            Список TokenSpec в порядке убывания приоритета
        """
        if self._cached_token_specs is None:
            self._cached_token_specs = self.registry.get_tokens_by_priority()
            logger.debug(f"Cached {len(self._cached_token_specs)} token specs")
        
        return self._cached_token_specs
    
    def _match_next_token(self, token_specs: List[TokenSpec]) -> Optional[Token]:
        """
        Пытается найти подходящий токен в текущей позиции.
        
        Args:
            token_specs: Отсортированные спецификации токенов
            
        Returns:
            Найденный токен или None
        """
        start_line, start_column = self.line, self.column
        start_position = self.position
        
        # Пробуем каждую спецификацию токена в порядке приоритета
        for spec in token_specs:
            match = spec.pattern.match(self.text, self.position)
            if match:
                matched_text = match.group(0)
                self._advance(len(matched_text))
                
                token = Token(
                    spec.name,
                    matched_text,
                    start_position,
                    start_line,
                    start_column
                )
                
                logger.debug(f"Matched token {spec.name}: '{matched_text}'")
                return token
        
        return None

    
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