"""Правила, определяющие, нужно ли исключить конкретный файл из листинга."""

from __future__ import annotations
from typing import Dict


def _significant_lines(text: str):
    """Возвращает непустые строки без комментариев."""
    for ln in text.splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            yield s


def should_skip_file(filename: str, text: str, cfg: Dict) -> bool:
    """
    True → файл исключается из листинга.

    Логика управляется полями listing_config.json:
    - skip_empty
    - skip_trivial_inits
    - trivial_init_max_noncomment
    """
    # 1) полностью пустой
    if cfg.get("skip_empty") and not text.strip():
        return True

    # 2) тривиальный __init__.py
    if cfg.get("skip_trivial_inits") and filename == "__init__.py":
        lines = list(_significant_lines(text))
        limit = int(cfg.get("trivial_init_max_noncomment", 1))
        if len(lines) <= limit and all(l in ("pass", "...") for l in lines):
            return True

    return False
