"""
Utilities for Scala adapter tests.

All Scala-specific test utilities are here.
"""

from pathlib import Path

from lg.adapters.context import LightweightContext
from lg.adapters.langs.scala import ScalaAdapter, ScalaCfg
from lg.stats.tokenizer import default_tokenizer


def make_adapter(cfg: ScalaCfg) -> ScalaAdapter:
    """
    Create Scala adapter with stub tokenizer.

    Use this for most tests to ensure deterministic behavior.
    """
    cfg.placeholders.min_savings_ratio = 0.0
    cfg.placeholders.min_abs_savings_if_none = 0
    return ScalaAdapter.bind_with_cfg(cfg, default_tokenizer())


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


__all__ = ["make_adapter", "lctx"]
