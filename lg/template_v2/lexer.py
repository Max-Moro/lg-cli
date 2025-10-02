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
            elif token.type.name == "PLACEHOLDER_START":
                # Токенизируем содержимое плейсхолдера (как в старом лексере)
                tokens.append(token)
                # Находим конец плейсхолдера
                end_pos = self._find_placeholder_end()
                if end_pos > self.position:
                    content = self.text[self.position:end_pos]
                    self._advance(len(content))
                    # Токенизируем содержимое плейсхолдера
                    content_tokens = self._tokenize_placeholder_content(content)
                    tokens.extend(content_tokens)
            elif token.type.name == "PLACEHOLDER_END":
                tokens.append(token)
            else:
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
        
        # Сначала проверяем специальные разделители (как в старом лексере)
        special_tokens = ["PLACEHOLDER_START", "DIRECTIVE_START", "COMMENT_START", 
                         "PLACEHOLDER_END", "DIRECTIVE_END", "COMMENT_END"]
        
        for token_name in special_tokens:
            if token_name in self.token_name_to_type:
                pattern_spec = next((spec for spec in self.registry.get_tokens_by_priority() 
                                  if spec.name == token_name), None)
                if pattern_spec:
                    match = pattern_spec.pattern.match(self.text, self.position)
                    if match:
                        value = match.group(0)
                        self._advance(len(value))
                        token_type = self.token_name_to_type[token_name]
                        return Token(token_type, value, start_pos, start_line, start_column)
        
        # Если не нашли специальных разделителей, считаем это текстом
        # Читаем до следующего специального символа или конца (как в старом лексере)
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
        Находит позицию следующей специальной последовательности
        (${, {%, {#, }, %}, #}) или конец текста.
        Копирует логику из старого лексера.
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
    
    def _find_placeholder_end(self) -> int:
        """Находит конец текущего плейсхолдера."""
        pos = self.position
        while pos < self.length:
            if self.text[pos] == '}':
                return pos
            pos += 1
        return self.length
    
    def _tokenize_placeholder_content(self, content: str) -> List[Token]:
        """
        Токенизирует содержимое плейсхолдера.
        
        Args:
            content: Содержимое между ${ и }
            
        Returns:
            Список токенов для содержимого плейсхолдера
        """
        if not content.strip():
            return []
        
        # Создаем временный лексер для содержимого
        temp_lexer = ModularLexer(self.registry)
        
        # Используем простую токенизацию внутри плейсхолдера
        temp_lexer.text = content
        temp_lexer.position = 0 
        temp_lexer.line = 1
        temp_lexer.column = 1
        temp_lexer.length = len(content)
        
        tokens = []
        
        while temp_lexer.position < temp_lexer.length:
            # Используем специальную токенизацию внутри плейсхолдера
            token = temp_lexer._tokenize_inside_placeholder()
            if token.type == DynamicTokenType(TokenType.EOF):
                break
            tokens.append(token)
        
        return tokens
    
    def _tokenize_inside_placeholder(self) -> Token:
        """Токенизирует содержимое внутри плейсхолдера (адаптировано из старого лексера)."""
        if self.position >= self.length:
            return Token(DynamicTokenType(TokenType.EOF), "", self.position, self.line, self.column)
        
        start_pos = self.position
        start_line = self.line
        start_column = self.column
        
        # Пропускаем пробелы
        import re
        whitespace_pattern = re.compile(r'[ \t]+')
        match = whitespace_pattern.match(self.text, self.position)
        if match:
            self._advance(len(match.group(0)))
            return self._tokenize_inside_placeholder()  # Рекурсивно продолжаем
        
        # Проверяем специальные символы для плейсхолдеров
        special_chars = {
            ':': 'COLON',
            '@': 'AT', 
            ',': 'COMMA',
            '[': 'LBRACKET',
            ']': 'RBRACKET',
            '#': 'HASH',
            '(': 'LPAREN',
            ')': 'RPAREN'
        }
        
        char = self.text[self.position]
        if char in special_chars:
            self._advance(1)
            token_type = self.token_name_to_type.get(special_chars[char], DynamicTokenType(special_chars[char]))
            return Token(token_type, char, start_pos, start_line, start_column)
        
        # Проверяем идентификаторы
        identifier_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_\-\/\.]*')
        match = identifier_pattern.match(self.text, self.position)
        if match:
            value = match.group(0)
            self._advance(len(value))
            token_type = self.token_name_to_type.get('IDENTIFIER', DynamicTokenType('IDENTIFIER'))
            return Token(token_type, value, start_pos, start_line, start_column)
        
        # Неожиданный символ
        char = self.text[self.position]
        from .tokens import LexerError
        raise LexerError(
            f"Unexpected character in placeholder: {char!r}",
            self.line, self.column, self.position
        )


__all__ = ["ModularLexer"]