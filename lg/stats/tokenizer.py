from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

import tiktoken
from tiktoken import Encoding

from .model import ResolvedModel

"""
Сервис подсчёта токенов.

Создаётся один раз на старте пайплайна на основе выбранной модели
и предоставляет простое текстовое API без привязки к Tree-sitter.
"""

DEFAULT_ENCODER = "cl100k_base"

class TokenService:
    """
    Обёртка над tiktoken с единым энкодером и встроенным кешированием.
    """

    def __init__(
            self,
            root: Optional[Path],
            model_id: Optional[str],
            *,
            encoder: Optional[Encoding] = None,
            cache=None
    ):
        self.root = root
        self.model_id = model_id
        self._enc: Optional[Encoding] = encoder
        self._model_info: Optional[ResolvedModel] = None
        self.cache = cache  # Кеш для токенов

    # ---------------- Internal ---------------- #
    def _get_encoder(self, cfg_name: str) -> Encoding:
        try:
            enc = tiktoken.get_encoding(cfg_name)
        except Exception:
            try:
                enc = tiktoken.encoding_for_model(cfg_name)
            except Exception:
                enc = tiktoken.get_encoding(DEFAULT_ENCODER)
        return enc

    # ---------------- Public API ---------------- #
    @property
    def enc(self) -> Encoding:
        """Ленивая инициализация энкодера."""
        if self._enc is None:
            from lg.stats.load import get_model_info
            self._model_info = get_model_info(self.root, self.model_id)
            self._enc = self._get_encoder(self._model_info.encoder)
        return self._enc

    @property
    def model_info(self) -> ResolvedModel:
        """Ленивая инициализация конфигурации AI-моделей."""
        if self.root is None:
            raise RuntimeError(
                "model_info недоступен для токенайзера без пути: "
                "токенайзер имеет только энкодер, но не имеет доступа к конфигурации AI-моделей"
            )
        if self._model_info is None:
            from lg.stats.load import get_model_info
            self._model_info = get_model_info(self.root, self.model_id)
            self._enc = self._get_encoder(self._model_info.encoder)
        return self._model_info

    @property
    def encoder_name(self):
        return self.enc.name

    def count_text(self, text: str) -> int:
        """Подсчитать токены в тексте."""
        if not text:
            return 0
        return len(self.enc.encode(text))
    
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
        
        # Получаем имя модели для кеша
        model_name = self.model_info.base if self.root else "default"
        
        # Пытаемся получить из кеша
        cached_tokens = self.cache.get_text_tokens(text, model_name)
        if cached_tokens is not None:
            return cached_tokens
        
        # Если нет в кеше, подсчитываем и сохраняем
        token_count = self.count_text(text)
        self.cache.put_text_tokens(text, model_name, token_count)
        
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


def default_tokenizer() -> TokenService:
    """Быстрое создание сервиса токенизации без обращения к конфигу."""
    return TokenService(
        root=None,
        model_id=None,
        encoder=tiktoken.get_encoding(DEFAULT_ENCODER),
        cache=None
    )
