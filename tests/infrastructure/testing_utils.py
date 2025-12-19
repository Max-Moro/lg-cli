"""
Testing utilities: stubs, mocks and other test helpers.

Unifies test stubs and utilities used in various tests.
"""

from __future__ import annotations

from pathlib import Path

from lg.adapters.context import LightweightContext


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


__all__ = ["lctx_md"]
