"""
Модульный лексический анализатор для шаблонизатора.

Собирает паттерны токенов из зарегистрированных плагинов и выполняет
токенизацию исходного текста шаблона.
"""

from __future__ import annotations

from typing import Dict, List, Pattern

from .registry import TemplateRegistry
from .tokens import Token, TokenType, DynamicTokenType, LexerError


class ModularLexer:
    """
    Лексический анализатор, собирающий паттерны токенов из плагинов.
    
    Использует зарегистрированные в TemplateRegistry токены для создания
    единого лексера, способного распознавать все типы конструкций.
    """
    
    def __init__(self, registry: TemplateRegistry):
        """
        Инициализирует лексер с указанным реестром.
        
        Args:
            registry: Реестр компонентов (по умолчанию - глобальный)
        """
        self.registry = registry
        
        # Паттерны токенов, отсортированные по приоритету
        self.token_patterns: List[tuple[str, Pattern[str]]] = []
        
        # Карта имен токенов в динамические типы
        self.token_name_to_type: Dict[str, DynamicTokenType] = {}
        
        # Инициализация паттернов
        self._initialize_patterns()
        
        # Позиционная информация
        self.text = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = 0
    
    def _initialize_patterns(self) -> None:
        """Собирает и сортирует паттерны токенов из реестра."""
        # Получаем токены, отсортированные по приоритету
        sorted_tokens = self.registry.get_tokens_by_priority()
        
        for token_spec in sorted_tokens:
            self.token_patterns.append((token_spec.name, token_spec.pattern))
            
            # Создаем DynamicTokenType для всех токенов
            try:
                # Пытаемся найти базовый TokenType
                base_token_type = TokenType[token_spec.name]
                dynamic_token = DynamicTokenType(base_token_type)
            except KeyError:
                # Создаем динамический токен
                dynamic_token = DynamicTokenType(token_spec.name)
            
            self.token_name_to_type[token_spec.name] = dynamic_token
    
    def tokenize(self, text: str) -> List[Token]:
        """
        Токенизирует входной текст с использованием зарегистрированных паттернов.
        
        Args:
            text: Исходный текст для токенизации
            
        Returns:
            Список токенов
            
        Raises:
            LexerError: При ошибке лексического анализа
        """
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        
        tokens: List[Token] = []
        
        while self.position < self.length:
            token = self._next_token()
            if token.type == TokenType.EOF:
                break
            tokens.append(token)
        
        # Добавляем EOF токен
        tokens.append(Token(DynamicTokenType(TokenType.EOF), "", self.position, self.line, self.column))
        
        return tokens
    
    def _next_token(self) -> Token:
        """
        Извлекает следующий токен из входного потока.
        
        Returns:
            Следующий токен
            
        Raises:
            LexerError: При невозможности распознать токен
        """
        if self.position >= self.length:
            return Token(DynamicTokenType(TokenType.EOF), "", self.position, self.line, self.column)
        
        start_pos = self.position
        start_line = self.line
        start_column = self.column
        
        # Пробуем каждый паттерн в порядке приоритета
        for token_name, pattern in self.token_patterns:
            match = pattern.match(self.text, self.position)
            if match:
                value = match.group(0)
                self._advance(len(value))
                
                # Получаем тип токена
                token_type = self.token_name_to_type.get(token_name, DynamicTokenType(TokenType.TEXT))
                
                return Token(token_type, value, start_pos, start_line, start_column)
        
        # Если ничего не подошло, пытаемся найти текст до следующего специального символа
        text_end = self._find_next_special_sequence()
        if text_end > self.position:
            value = self.text[self.position:text_end]
            self._advance(len(value))
            return Token(DynamicTokenType(TokenType.TEXT), value, start_pos, start_line, start_column)
        
        # Неожиданный символ
        char = self.text[self.position]
        raise LexerError(
            f"Unexpected character: {char!r}",
            self.line, self.column, self.position
        )
    
    def _advance(self, count: int) -> None:
        """
        Перемещает позицию на указанное количество символов.
        
        Args:
            count: Количество символов для продвижения
        """
        for i in range(count):
            if self.position >= self.length:
                break
                
            char = self.text[self.position]
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            
            self.position += 1
    
    def _find_next_special_sequence(self) -> int:
        """
        Находит позицию следующей специальной последовательности.
        
        Returns:
            Позицию следующего специального токена или конец текста
        """
        current_pos = self.position
        
        # Ищем ближайшее совпадение с любым паттерном
        min_pos = self.length
        
        for _, pattern in self.token_patterns:
            match = pattern.search(self.text, current_pos)
            if match and match.start() < min_pos:
                min_pos = match.start()
        
        return min_pos if min_pos > current_pos else self.length


__all__ = ["ModularLexer"]