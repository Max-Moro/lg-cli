"""
Утилиты для тестирования: стабы, моки и другие тестовые хелперы.

Унифицирует тестовые заглушки и утилиты, которые используются 
в различных тестах.
"""

from __future__ import annotations

from lg.stats import TokenService


class TokenServiceStub(TokenService):
    """Тестовый стаб TokenService с дефолтным энкодером."""

    def is_economical(self, original: str, replacement: str, *, min_ratio: float, replacement_is_none: bool,
                      min_abs_savings_if_none: int) -> bool:
        """Позволяет в тестах делать замену плейсхолдеров всегда."""
        return True


def stub_tokenizer() -> TokenService:
    """Быстрое создание сервиса токенизации без обращения к конфигу."""
    import tiktoken
    from lg.stats.tokenizer import DEFAULT_ENCODER
    return TokenServiceStub(
        root=None,
        model_id=None,
        encoder=tiktoken.get_encoding(DEFAULT_ENCODER)
    )


__all__ = ["TokenServiceStub", "stub_tokenizer"]