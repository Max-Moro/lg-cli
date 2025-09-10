from __future__ import annotations

"""
Единый сервис подсчёта токенов для пайплайна и оптимизаторов.

Создаётся один раз на старте пайплайна на основе выбранной модели
и предоставляет простое текстовое API без привязки к Tree-sitter.
"""

from dataclasses import dataclass
from typing import Tuple

import tiktoken


@dataclass(frozen=True)
class TokenService:
    """
    Обёртка над tiktoken с единым энкодером.

    Методы работают со строками (UTF-8). Привязки к AST/байтовым диапазонам нет.
    """

    encoder_name: str

    def __post_init__(self):
        # Ленивая инициализация энкодера при первом обращении
        object.__setattr__(self, "_enc", None)

    # ---------------- Internal ---------------- #
    def _get_encoder(self):
        enc = getattr(self, "_enc", None)
        if enc is None:
            try:
                enc = tiktoken.get_encoding(self.encoder_name)
            except Exception:
                try:
                    enc = tiktoken.encoding_for_model(self.encoder_name)
                except Exception:
                    enc = tiktoken.get_encoding("cl100k_base")
            object.__setattr__(self, "_enc", enc)
        return enc

    # ---------------- Public API ---------------- #
    def count_text(self, text: str) -> int:
        """Подсчитать токены в тексте."""
        if not text:
            return 0
        enc = self._get_encoder()
        return len(enc.encode(text))

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
                       min_abs_savings_if_none: int | None = None) -> bool:
        """
        Проверка целесообразности замены.

        - Для обычных плейсхолдеров применяется только порог отношения savings/replacement ≥ min_ratio.
        - Для "пустых" замен (replacement_is_none=True) дополнительно может применяться абсолютный порог
          экономии токенов (min_abs_savings_if_none), чтобы избежать микроскопических удалений.
        """
        orig, repl, savings, ratio = self.compare_texts(original, replacement)

        if replacement_is_none and (min_abs_savings_if_none or 0) > 0:
            if savings < int(min_abs_savings_if_none):
                return False

        return ratio >= float(min_ratio)


