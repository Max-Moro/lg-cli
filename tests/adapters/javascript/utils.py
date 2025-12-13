"""Utilities for JavaScript adapter tests."""

from pathlib import Path
from lg.adapters.javascript import JavaScriptAdapter
from lg.adapters.code_model import CodeCfg
from lg.adapters.context import LightweightContext
from lg.stats.tokenizer import default_tokenizer
from tests.infrastructure import stub_tokenizer


def make_adapter(cfg: CodeCfg) -> JavaScriptAdapter:
    """Create JavaScript adapter with stub tokenizer."""
    adapter = JavaScriptAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    # Initialize literal pipeline after config override
    if cfg.literals.max_tokens is not None:
        from lg.adapters.optimizations import LiteralPipeline
        adapter.literal_pipeline = LiteralPipeline(adapter)
    else:
        adapter.literal_pipeline = None
    return adapter


def make_adapter_real(cfg: CodeCfg) -> JavaScriptAdapter:
    """Create JavaScript adapter with real tokenizer."""
    adapter = JavaScriptAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    # Initialize literal pipeline after config override
    if cfg.literals.max_tokens is not None:
        from lg.adapters.optimizations import LiteralPipeline
        adapter.literal_pipeline = LiteralPipeline(adapter)
    else:
        adapter.literal_pipeline = None
    return adapter


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


__all__ = ["make_adapter", "make_adapter_real", "lctx"]
