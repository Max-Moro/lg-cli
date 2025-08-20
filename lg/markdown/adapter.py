from __future__ import annotations

from typing import Tuple

from .model import MarkdownCfg
from .normalize import normalize_markdown


def process_markdown(text: str, cfg: MarkdownCfg, *, group_size: int, mixed: bool) -> Tuple[str, dict]:
    """
    Временный пайплайн адаптера (Этап 0–1):
      • только снятие H1 и normalize max_heading_level
      • возвращает (text, meta)
    """
    # cfg может быть None, если bind() не вызывался — трактуем как "без нормализации"
    out_text, meta = normalize_markdown(text, max_heading_level=cfg.max_heading_level, group_size=group_size, mixed=mixed)
    return out_text, meta
