"""
Utilities for Kotlin adapter tests.

All Kotlin-specific test utilities are here.
"""

from pathlib import Path

from lg.adapters.kotlin import KotlinAdapter, KotlinCfg
from lg.adapters.context import LightweightContext
from lg.stats.tokenizer import default_tokenizer
from tests.infrastructure import stub_tokenizer


def make_adapter(cfg: KotlinCfg) -> KotlinAdapter:
    """
    Create Kotlin adapter with stub tokenizer.

    Use this for most tests to ensure deterministic behavior.
    """
    adapter = KotlinAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_adapter_real(cfg: KotlinCfg) -> KotlinAdapter:
    """
    Create Kotlin adapter with real tokenizer.

    Use this when testing actual token counting/mathematics.
    """
    adapter = KotlinAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


def lctx(
    code: str,
    file_path: Path | None = None,
    group_size: int = 1
) -> LightweightContext:
    """
    Create lightweight context for Kotlin code.

    Args:
        code: Kotlin source code
        file_path: Optional file path (defaults to /test/file.kt)
        group_size: Size of file group for statistics

    Returns:
        LightweightContext ready for adapter processing
    """
    if file_path is None:
        file_path = Path("/test/file.kt")

    return LightweightContext(
        file_path=file_path,
        raw_text=code,
        group_size=group_size,
        template_ctx=None,
        file_label=None
    )


__all__ = ["make_adapter", "make_adapter_real", "lctx"]
