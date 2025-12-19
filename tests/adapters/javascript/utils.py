"""Utilities for JavaScript adapter tests."""

from pathlib import Path

from lg.adapters.context import LightweightContext
from lg.adapters.javascript import JavaScriptAdapter, JavaScriptCfg
from lg.stats.tokenizer import default_tokenizer


def make_adapter(cfg: JavaScriptCfg) -> JavaScriptAdapter:
    """Create JavaScript adapter with stub tokenizer."""
    cfg.placeholders.min_savings_ratio = 0.0
    cfg.placeholders.min_abs_savings_if_none = 0
    return JavaScriptAdapter.bind_with_cfg(cfg, default_tokenizer())


def lctx(code: str, file_path: Path | None = None, group_size: int = 1) -> LightweightContext:
    """Create lightweight context for JavaScript code."""
    if file_path is None:
        file_path = Path("/test/file.js")

    return LightweightContext(
        file_path=file_path,
        raw_text=code,
        group_size=group_size,
        template_ctx=None,
        file_label=None
    )


__all__ = ["make_adapter", "lctx"]
