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


def lctx_md(raw_text: str = "# Test Markdown", group_size: int = 1) -> LightweightContext:
    """
    Creates LightweightContext for a Markdown file.

    Note: Used by tests/markdown/. For adapter tests, use local utils.
    """
    test_path = Path("test.md")
    return LightweightContext(
        file_path=test_path,
        raw_text=raw_text,
        group_size=group_size,
        file_label="test.md"
    )


__all__ = ["TokenServiceStub", "stub_tokenizer", "lctx_md"]
