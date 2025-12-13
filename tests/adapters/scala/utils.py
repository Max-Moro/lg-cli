"""
Utilities for Scala adapter tests.

All Scala-specific test utilities are here.
"""

from pathlib import Path

from lg.adapters.scala import ScalaAdapter, ScalaCfg
from lg.adapters.context import LightweightContext
from lg.stats.tokenizer import default_tokenizer
from tests.infrastructure import stub_tokenizer


def make_adapter(cfg: ScalaCfg) -> ScalaAdapter:
    """
    Create Scala adapter with stub tokenizer.

    Use this for most tests to ensure deterministic behavior.
    """
    adapter = ScalaAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    # Initialize literal pipeline after config override
    if cfg.literals.max_tokens is not None:
        from lg.adapters.optimizations import LiteralPipeline
        adapter.literal_pipeline = LiteralPipeline(adapter)
    else:
        adapter.literal_pipeline = None
    return adapter


def make_adapter_real(cfg: ScalaCfg) -> ScalaAdapter:
    """
    Create Scala adapter with real tokenizer.

    Use this when testing actual token counting/mathematics.
    """
    adapter = ScalaAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    # Initialize literal pipeline after config override
    if cfg.literals.max_tokens is not None:
        from lg.adapters.optimizations import LiteralPipeline
        adapter.literal_pipeline = LiteralPipeline(adapter)
    else:
        adapter.literal_pipeline = None
    return adapter


def lctx(
    code: str,
    file_path: Path | None = None,
    group_size: int = 1
) -> LightweightContext:
    """
    Create lightweight context for Scala code.

    Args:
        code: Scala source code
        file_path: Optional file path (defaults to /test/file.scala)
        group_size: Size of file group for statistics

    Returns:
        LightweightContext ready for adapter processing
    """
    if file_path is None:
        file_path = Path("/test/file.scala")

    return LightweightContext(
        file_path=file_path,
        raw_text=code,
        group_size=group_size,
        template_ctx=None,
        file_label=None
    )


__all__ = ["make_adapter", "make_adapter_real", "lctx"]
