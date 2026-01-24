"""
Helper functions for loading templates and contexts.

Provides utilities for loading template and context files from lg-cfg/ directories.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

# Document suffixes
TPL_SUFFIX = ".tpl.md"
CTX_SUFFIX = ".ctx.md"


def load_from_cfg(cfg_root: Path, resource: str, *, suffix: str) -> Tuple[Path, str]:
    """
    Load file from lg-cfg/: <cfg_root>/<resource><suffix>.
    """
    from ..migrate import ensure_cfg_actual
    ensure_cfg_actual(cfg_root)
    p = (cfg_root / f"{resource}{suffix}").resolve()
    if not p.is_file():
        raise RuntimeError(f"Resource not found: {p}")
    return p, p.read_text(encoding="utf-8", errors="ignore")


def load_context_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Context: <cfg_root>/<name>.ctx.md"""
    return load_from_cfg(cfg_root, name, suffix=CTX_SUFFIX)


def load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
    """Template: <cfg_root>/<name>.tpl.md"""
    return load_from_cfg(cfg_root, name, suffix=TPL_SUFFIX)


def list_contexts(root: Path) -> List[str]:
    """
    List available contexts (ONLY *.ctx.md) relative to lg-cfg/.
    """
    from ..paths import cfg_root
    base = cfg_root(root)
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in base.rglob(f"*{CTX_SUFFIX}"):
        rel = p.relative_to(base).as_posix()
        out.append(rel[: -len(CTX_SUFFIX)])
    out.sort()
    return out


__all__ = [
    "load_from_cfg",
    "load_context_from",
    "load_template_from",
    "list_contexts",
    "TPL_SUFFIX",
    "CTX_SUFFIX"
]