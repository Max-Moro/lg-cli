from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

import tiktoken
from tiktoken import Encoding

from lg.stats import get_model_info

"""
Сервис подсчёта токенов.

Создаётся один раз на старте пайплайна на основе выбранной модели
и предоставляет простое текстовое API без привязки к Tree-sitter.
"""

DEFAULT_ENCODER = "cl100k_base"

class TokenService:
    """
    Обёртка над tiktoken с единым энкодером.

    Методы работают со строками (UTF-8). Привязки к AST/байтовым диапазонам нет.
    """

    def __init__(
            self,
            root: Optional[Path],
            model_id: Optional[str],
            *,
            encoder: Optional[Encoding] = None
    ):
        self.root = root
        self.model_id = model_id
        self._enc: Optional[Encoding] = encoder

    # ---------------- Internal ---------------- #
    @property
    def enc(self) -> Encoding:
        """Ленивая инициализация энкодера."""
        if self._enc is None:
            model_info = get_model_info(self.root, self.model_id)
            self._enc = self._get_encoder(model_info.encoder)
        return self._enc

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
    def encoder_name(self):
        return self.enc.name

    def count_text(self, text: str) -> int:
        """Подсчитать токены в тексте."""
        if not text:
            return 0
        return len(self.enc.encode(text))

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


def default_tokenizer() -> TokenService:
    """Быстрое создание сервиса токенизации без обращения к конфигу."""
    return TokenService(
        root=None,
        model_id=None,
        encoder=tiktoken.get_encoding(DEFAULT_ENCODER)
    )
