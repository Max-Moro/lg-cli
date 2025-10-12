"""
Утилиты для тестирования: стабы, моки и другие тестовые хелперы.

Унифицирует тестовые заглушки и утилиты, которые используются 
в различных тестах.
"""

from __future__ import annotations

from pathlib import Path

from lg.adapters.context import LightweightContext
from lg.stats import TokenService


class TokenServiceStub(TokenService):
    """Тестовый стаб TokenService с дефолтным энкодером."""

    def is_economical(self, original: str, replacement: str, *, min_ratio: float, replacement_is_none: bool,
                      min_abs_savings_if_none: int) -> bool:
        """Позволяет в тестах делать замену плейсхолдеров всегда."""
        return True


def stub_tokenizer() -> TokenService:
    """Быстрое создание сервиса токенизации без обращения к конфигу."""
    return TokenServiceStub(
        root=None,
        lib="tiktoken",
        encoder="cl100k_base"
    )


def lctx(
        raw_text: str = "# Test content",
        filename: str = "test.py",
        group_size: int = 1,
        file_label: str = None
) -> LightweightContext:
    """
    Создает stub LightweightContext для тестов.

    Args:
        raw_text: Содержимое файла
        filename: Имя файла
        group_size: Размер группы
        file_label: Метка файла для рендеринга

    Returns:
        LightweightContext для использования в тестах
    """
    test_path = Path(filename)
    if file_label is None:
        file_label = filename
    return LightweightContext(
        file_path=test_path,
        raw_text=raw_text,
        group_size=group_size,
        file_label=file_label
    )


def lctx_py(raw_text: str = "# Test Python", group_size: int = 1) -> LightweightContext:
    """Создает LightweightContext для Python файла."""
    return lctx(raw_text=raw_text, filename="test.py", group_size=group_size)


def lctx_ts(raw_text: str = "// Test TypeScript", group_size: int = 1) -> LightweightContext:
    """Создает LightweightContext для TypeScript файла.""" 
    return lctx(raw_text=raw_text, filename="test.ts", group_size=group_size)


def lctx_md(raw_text: str = "# Test Markdown", group_size: int = 1) -> LightweightContext:
    """Создает LightweightContext для Markdown файла."""
    return lctx(raw_text=raw_text, filename="test.md", group_size=group_size)


def lctx_kt(raw_text: str = "// Test Kotlin", group_size: int = 1) -> LightweightContext:
    """Создает LightweightContext для Kotlin файла."""
    return lctx(raw_text=raw_text, filename="test.kt", group_size=group_size)


__all__ = ["TokenServiceStub", "stub_tokenizer", "lctx", "lctx_py", "lctx_ts", "lctx_md", "lctx_kt"]