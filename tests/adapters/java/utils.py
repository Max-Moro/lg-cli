"""
Utilities for Java adapter tests.

All Java-specific test utilities are here.
"""

from pathlib import Path

from lg.adapters.java import JavaAdapter, JavaCfg
from lg.adapters.context import LightweightContext
from lg.stats.tokenizer import default_tokenizer
from tests.infrastructure import stub_tokenizer


def make_adapter(cfg: JavaCfg) -> JavaAdapter:
    """
    Create Java adapter with stub tokenizer.

    Use this for most tests to ensure deterministic behavior.
    """
    return JavaAdapter.bind_with_cfg(cfg, stub_tokenizer())


def make_adapter_real(cfg: JavaCfg) -> JavaAdapter:
    """
    Create Java adapter with real tokenizer.

    Use this when testing actual token counting/mathematics.
    """
    return JavaAdapter.bind_with_cfg(cfg, default_tokenizer())


def lctx(
    code: str,
    file_path: Path | None = None,
    group_size: int = 1
) -> LightweightContext:
    """
    Create lightweight context for Java code.

    Args:
        code: Java source code
        file_path: Optional file path (defaults to /test/file.java)
        group_size: Size of file group for statistics

    Returns:
        LightweightContext ready for adapter processing
    """
    if file_path is None:
        file_path = Path("/test/file.java")

    return LightweightContext(
        file_path=file_path,
        raw_text=code,
        group_size=group_size,
        template_ctx=None,
        file_label=None
    )


__all__ = ["make_adapter", "make_adapter_real", "lctx"]
