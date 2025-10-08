from __future__ import annotations

from pathlib import Path
from typing import Tuple

from .tokenizers import BaseTokenizer, create_tokenizer

"""
Сервис подсчёта токенов.

Создаётся один раз на старте пайплайна и предоставляет
унифицированное API для работы с разными токенизаторами.
"""

class TokenService:
    """
    Обёртка над BaseTokenizer с встроенным кешированием.
    """

    def __init__(
        self,
        root: Path,
        lib: str,
        encoder: str,
        *,
        cache=None
    ):
        """
        Args:
            root: Корень проекта
            lib: Имя библиотеки (tiktoken, tokenizers, sentencepiece)
            encoder: Имя энкодера/модели
            cache: Кеш для токенов (опционально)
        """
        self.root = root
        self.lib = lib
        self.encoder = encoder
        self.cache = cache
        
        # Создаем токенизатор
        self._tokenizer = create_tokenizer(lib, encoder, root)

    @property
    def tokenizer(self) -> BaseTokenizer:
        """Возвращает базовый токенизатор."""
        return self._tokenizer

    @property
    def encoder_name(self) -> str:
        """Имя энкодера."""
        return self.encoder

    def count_text(self, text: str) -> int:
        """Подсчитать токены в тексте."""
        return self._tokenizer.count_tokens(text)
    
    def count_text_cached(self, text: str) -> int:
        """
        Подсчитать токены в тексте с использованием кеша.
        
        Args:
            text: Текст для подсчета токенов
            
        Returns:
            Количество токенов
        """
        if not text:
            return 0
        
        # Если нет кеша, просто считаем
        if not self.cache:
            return self.count_text(text)
        
        # Пытаемся получить из кеша
        # Ключ: lib:encoder
        cache_key = f"{self.lib}:{self.encoder}"
        cached_tokens = self.cache.get_text_tokens(text, cache_key)
        if cached_tokens is not None:
            return cached_tokens
        
        # Если нет в кеше, подсчитываем и сохраняем
        token_count = self.count_text(text)
        self.cache.put_text_tokens(text, cache_key, token_count)
        
        return token_count

    def compare_texts(self, original: str, replacement: str) -> Tuple[int, int, int, float]:
        """
        Сравнить стоимость оригинала и замены.

        Returns: (orig_tokens, repl_tokens, savings, ratio)
        ratio = savings / max(repl_tokens, 1)
        """
        orig = self.count_text(original)
        repl = self.count_text(replacement)
        savings = max(0, orig - repl)
        ratio = savings / float(max(repl, 1))
        return orig, repl, savings, ratio

    def is_economical(self, original: str, replacement: str, *, min_ratio: float, replacement_is_none: bool,
                       min_abs_savings_if_none: int) -> bool:
        """
        Проверка целесообразности замены.

        - Для обычных плейсхолдеров применяется только порог отношения savings/replacement ≥ min_ratio.
        - Для "пустых" замен (replacement_is_none=True) дополнительно может применяться абсолютный порог
          экономии токенов (min_abs_savings_if_none), чтобы избежать микроскопических удалений.
        """
        orig, repl, savings, ratio = self.compare_texts(original, replacement)

        if replacement_is_none and savings < min_abs_savings_if_none:
            return False

        return ratio >= float(min_ratio)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Урезает текст до указанного количества токенов используя пропорциональное отношение.
        
        Args:
            text: Исходный текст для урезания
            max_tokens: Максимальное количество токенов
            
        Returns:
            Урезанный текст, который помещается в указанный лимит токенов
        """
        if not text:
            return ""
        
        current_tokens = self.count_text(text)
        if current_tokens <= max_tokens:
            return text
        
        # Пропорциональное урезание по символам
        ratio = max_tokens / current_tokens
        target_length = int(len(text) * ratio)
        
        # Урезаем до целевой длины, но не меньше 1 символа
        target_length = max(1, target_length)
        trimmed = text[:target_length].rstrip()
        
        return trimmed
