"""
Контекстно-зависимый лексический анализатор для модульного шаблонизатора.

Использует контекстные группы токенов для эффективной токенизации
и предотвращения коллизий между плагинами.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from .base import TokenSpec, TokenContext
from .tokens import Token, TokenType

if TYPE_CHECKING:
    from .registry import TemplateRegistry

logger = logging.getLogger(__name__)


class ContextualLexer:
    """
    Контекстно-зависимый лексический анализатор.
    
    Отслеживает активные контексты и применяет только релевантные токены,
    что повышает производительность и предотвращает коллизии.
    """
    
    def __init__(self, registry: "TemplateRegistry"):
        """
        Инициализирует лексер с реестром плагинов.
        
        Args:
            registry: Реестр с зарегистрированными токенами и контекстами
        """
        self.registry = registry
        
        # Позиционная информация
        self.text = ""
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = 0
        
        # Стек активных контекстов для вложенных конструкций
        self.context_stack: List[TokenContext] = []
        
        # Кэшированные спецификации токенов
        self._global_token_cache: Optional[List[TokenSpec]] = None
        self._context_token_cache: Dict[str, List[TokenSpec]] = {}

    def tokenize(self, text: str) -> List[Token]:
        """
        Контекстно-зависимая токенизация.
        
        Применяет только релевантные токены в зависимости от текущего контекста,
        автоматически обрабатывая входы и выходы из контекстных областей.
        
        Args:
            text: Исходный текст для токенизации
            
        Returns:
            Список токенов
            
        Raises:
            LexerError: При ошибке токенизации
        """
        self._initialize_tokenization(text)
        
        tokens: List[Token] = []
        
        while self.position < self.length:
            token = self._match_next_token()
            
            if token is None:
                # Не удалось найти подходящий токен - обрабатываем как текст
                token = self._handle_unparsed_content()
            
            if token and token.value:  # Пропускаем токены с пустым содержимым
                tokens.append(token)
                self._update_context_stack(token)
        
        # Добавляем EOF токен
        tokens.append(Token(TokenType.EOF.value, "", self.position, self.line, self.column))
        
        logger.debug(f"Tokenized text into {len(tokens)} tokens with {len(self.context_stack)} active contexts")
        return tokens
    
    def _initialize_tokenization(self, text: str) -> None:
        """Инициализирует состояние для новой токенизации."""
        self.text = text
        self.position = 0
        self.line = 1
        self.column = 1
        self.length = len(text)
        self.context_stack = []
        
        # Сбрасываем кэши контекстных токенов
        self._context_token_cache.clear()
        
        logger.debug(f"Initialized tokenization for text of length {self.length}")
    
    def _match_next_token(self) -> Optional[Token]:
        """
        Пытается найти подходящий токен в текущей позиции.
        
        Использует контекстную фильтрацию для оптимизации производительности
        и предотвращения ложных срабатываний.
        
        Returns:
            Найденный токен или None
        """
        start_line, start_column = self.line, self.column
        start_position = self.position
        
        # Получаем токены, доступные в текущем контексте
        available_specs = self._get_available_token_specs()
        
        # Пробуем каждую спецификацию токена в порядке приоритета
        for spec in available_specs:
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
                
                logger.debug(f"Matched token {spec.name}: '{matched_text}' in context {self._get_context_name()}")
                return token
        
        return None
    
    def _get_available_token_specs(self) -> List[TokenSpec]:
        """
        Возвращает спецификации токенов, доступные в текущем контексте.
        
        Использует кэширование для повышения производительности.
        
        Returns:
            Отфильтрованный и отсортированный список токенов
        """
        if not self.context_stack:
            # В глобальном контексте: кэшируем глобальные токены
            return self._get_global_tokens()
        
        # В специфическом контексте: используем кэш для контекста
        current_context = self.context_stack[-1]
        context_key = f"{current_context.name}_{len(self.context_stack)}"
        
        if context_key not in self._context_token_cache:
            self._context_token_cache[context_key] = self._build_context_tokens(current_context)
        
        return self._context_token_cache[context_key]
    
    def _get_global_tokens(self) -> List[TokenSpec]:
        """
        Возвращает токены для глобального контекста с кэшированием.
        
        Returns:
            Список глобальных токенов и открывающих токенов контекстов
        """
        if self._global_token_cache is None:
            # Получаем все зарегистрированные токены
            all_tokens = self.registry.get_tokens_by_priority()
            
            # В глобальном контексте доступны:
            # 1. Глобальные токены (TEXT, EOF и т.д.)
            # 2. Открывающие токены всех контекстов
            global_tokens = []
            opening_tokens = set()
            
            # Собираем открывающие токены из всех контекстов
            for context in self.registry.get_all_token_contexts():
                opening_tokens.update(context.open_tokens)
            
            # Фильтруем токены
            for token_spec in all_tokens:
                # Включаем, если токен:
                # - глобальный (TEXT, EOF, и другие базовые)
                # - или является открывающим для какого-либо контекста
                if self._is_global_token(token_spec) or token_spec.name in opening_tokens:
                    global_tokens.append(token_spec)
            
            self._global_token_cache = global_tokens
            logger.debug(f"Built global token cache with {len(global_tokens)} tokens")
        
        return self._global_token_cache
    
    def _build_context_tokens(self, context: TokenContext) -> List[TokenSpec]:
        """
        Строит список токенов для указанного контекста.
        
        Args:
            context: Контекст для построения списка токенов
            
        Returns:
            Отсортированный список токенов для контекста
        """
        all_tokens = self.registry.get_tokens_by_priority()
        context_tokens = []
        
        # Определяем доступные имена токенов для контекста
        available_token_names = set()
        
        # 1. Закрывающие токены контекста (всегда доступны)
        available_token_names.update(context.close_tokens)
        
        # 2. Внутренние токены контекста
        available_token_names.update(context.inner_tokens)
        
        # 3. Если разрешена вложенность, добавляем открывающие токены других контекстов
        if context.allow_nesting:
            for other_context in self.registry.get_all_token_contexts():
                if other_context.name != context.name:  # Исключаем текущий контекст
                    available_token_names.update(other_context.open_tokens)
        
        # Фильтруем токены по доступным именам
        for token_spec in all_tokens:
            if token_spec.name in available_token_names:
                context_tokens.append(token_spec)
        
        logger.debug(
            f"Built context tokens for '{context.name}': {len(context_tokens)} tokens, "
            f"nesting={context.allow_nesting}"
        )
        
        return context_tokens
    
    def _is_global_token(self, token_spec: TokenSpec) -> bool:
        """
        Проверяет, является ли токен глобальным.
        
        Глобальные токены доступны вне всех контекстов.
        
        Args:
            token_spec: Спецификация токена
            
        Returns:
            True если токен глобальный
        """
        # Базовые глобальные токены
        global_token_names = {TokenType.TEXT.value, TokenType.EOF.value}
        
        return token_spec.name in global_token_names
    
    def _update_context_stack(self, token: Token) -> None:
        """
        Обновляет стек контекстов на основе токена.
        
        Args:
            token: Токен, который может изменить контекст
        """
        original_stack_size = len(self.context_stack)
        
        # Проверяем, является ли токен закрывающим для текущего контекста
        if self.context_stack and token.type in self.context_stack[-1].close_tokens:
            closed_context = self.context_stack.pop()
            logger.debug(f"Closed context '{closed_context.name}' with token '{token.type}'")
            
            # Очищаем кэш для закрытого контекста
            self._invalidate_context_cache()
            return
        
        # Проверяем, является ли токен открывающим для какого-либо контекста
        for context in self.registry.get_all_token_contexts():
            if token.type in context.open_tokens:
                self.context_stack.append(context)
                logger.debug(f"Opened context '{context.name}' with token '{token.type}'")
                
                # Очищаем кэш для нового контекста
                self._invalidate_context_cache()
                return
        
        # Логируем, если контекст не изменился (для отладки)
        if len(self.context_stack) == original_stack_size:
            logger.debug(f"Token '{token.type}' did not change context (current: {self._get_context_name()})")
    
    def _invalidate_context_cache(self) -> None:
        """Очищает кэш контекстных токенов при изменении стека контекстов."""
        self._context_token_cache.clear()
    
    def _get_context_name(self) -> str:
        """Возвращает имя текущего контекста для логирования."""
        if not self.context_stack:
            return "global"
        return self.context_stack[-1].name
    
    def _handle_unparsed_content(self) -> Token:
        """
        Обрабатывает содержимое, которое не удалось распарсить как специальный токен.
        
        Собирает непрерывный текст до следующего потенциального специального токена.
        
        Returns:
            Токен TEXT с собранным содержимым
        """
        start_line, start_column = self.line, self.column
        start_position = self.position
        
        # Собираем символы до следующего потенциального специального токена
        collected_text = ""
        
        while self.position < self.length:
            # Проверяем, может ли текущая позиция быть началом специального токена
            if self._could_be_special_token_start():
                break
            
            # Добавляем символ к тексту
            collected_text += self.text[self.position]
            self._advance(1)
        
        # Если не собрали ничего, берем хотя бы один символ чтобы не зациклиться
        if not collected_text and self.position < self.length:
            collected_text = self.text[self.position]
            self._advance(1)
        
        token = Token(
            TokenType.TEXT.value,
            collected_text,
            start_position,
            start_line,
            start_column
        )
        
        logger.debug(f"Created TEXT token: '{collected_text[:20]}...' in context {self._get_context_name()}")
        return token
    
    def _could_be_special_token_start(self) -> bool:
        """
        Проверяет, может ли текущая позиция быть началом специального токена.
        
        Используется для оптимизации сбора TEXT токенов.
        
        Returns:
            True если в текущей позиции может начинаться специальный токен
        """
        if self.position >= self.length:
            return False
        
        # Получаем доступные токены для текущего контекста
        available_specs = self._get_available_token_specs()
        
        # Проверяем, может ли какой-либо токен начинаться с текущей позиции
        for spec in available_specs:
            if spec.name == TokenType.TEXT.value:  # Пропускаем TEXT токен
                continue
                
            # Проверяем только начало паттерна для оптимизации
            if spec.pattern.match(self.text, self.position):
                return True
        
        return False
    
    def _advance(self, count: int) -> None:
        """
        Перемещает позицию на указанное количество символов.
        
        Обновляет номера строк и колонок для корректного отслеживания позиции.
        
        Args:
            count: Количество символов для продвижения
        """
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


__all__ = ["ContextualLexer"]