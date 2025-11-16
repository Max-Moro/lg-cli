"""
Testing utilities: stubs, mocks and other test helpers.

Unifies test stubs and utilities used in various tests.
"""

from __future__ import annotations

from pathlib import Path

from lg.adapters.context import LightweightContext
from lg.stats import TokenService


class TokenServiceStub(TokenService):
    """Test stub TokenService with default encoder."""

    def is_economical(self, original: str, replacement: str, *, min_ratio: float, replacement_is_none: bool,
                      min_abs_savings_if_none: int) -> bool:
        """Always allows placeholder replacement in tests."""
        return True


def stub_tokenizer() -> TokenService:
    """Quick creation of tokenization service without config access."""
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
    Creates a stub LightweightContext for tests.

    Args:
        raw_text: File content
        filename: File name
        group_size: Group size
        file_label: File label for rendering

    Returns:
        LightweightContext for use in tests
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
    """Creates LightweightContext for a Python file."""
    return lctx(raw_text=raw_text, filename="test.py", group_size=group_size)


def lctx_ts(raw_text: str = "// Test TypeScript", group_size: int = 1) -> LightweightContext:
    """Creates LightweightContext for a TypeScript file."""
    return lctx(raw_text=raw_text, filename="test.ts", group_size=group_size)


def lctx_md(raw_text: str = "# Test Markdown", group_size: int = 1) -> LightweightContext:
    """Creates LightweightContext for a Markdown file."""
    return lctx(raw_text=raw_text, filename="test.md", group_size=group_size)


def lctx_kt(raw_text: str = "// Test Kotlin", group_size: int = 1) -> LightweightContext:
    """Creates LightweightContext for a Kotlin file."""
    return lctx(raw_text=raw_text, filename="test.kt", group_size=group_size)


__all__ = ["TokenServiceStub", "stub_tokenizer", "lctx", "lctx_py", "lctx_ts", "lctx_md", "lctx_kt"]