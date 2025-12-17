"""
Utilities for Python adapter tests.

All Python-specific test utilities are here.
"""

from pathlib import Path

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.context import LightweightContext
from lg.stats.tokenizer import default_tokenizer
from tests.infrastructure import stub_tokenizer


def make_adapter(cfg: PythonCfg) -> PythonAdapter:
    """
    Create Python adapter with stub tokenizer.

    Use this for most tests to ensure deterministic behavior.
    """
    return PythonAdapter.bind_with_cfg(cfg, stub_tokenizer())


def make_adapter_real(cfg: PythonCfg) -> PythonAdapter:
    """
    Create Python adapter with real tokenizer.

    Use this when testing actual token counting/mathematics.
    """
    return PythonAdapter.bind_with_cfg(cfg, default_tokenizer())


def lctx(
    code: str,
    file_path: Path | None = None,
    group_size: int = 1
) -> LightweightContext:
    """
    Create lightweight context for Python code.

    Args:
        code: Python source code
        file_path: Optional file path (defaults to /test/file.py)
        group_size: Size of file group for statistics

    Returns:
        LightweightContext ready for adapter processing
    """
    if file_path is None:
        file_path = Path("/test/file.py")

    return LightweightContext(
        file_path=file_path,
        raw_text=code,
        group_size=group_size,
        template_ctx=None,
        file_label=None
    )


__all__ = ["make_adapter", "make_adapter_real", "lctx"]
