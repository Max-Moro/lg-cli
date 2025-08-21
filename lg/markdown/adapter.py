from __future__ import annotations

from typing import Tuple

from .intervals import build_drop_intervals
from .model import MarkdownCfg, MarkdownDropCfg, PlaceholderPolicy
from .normalize import normalize_markdown
from .parser import parse_markdown
from .transform import apply_intervals_with_placeholders


def process_markdown(text: str, cfg: MarkdownCfg, *, group_size: int, mixed: bool) -> Tuple[str, dict]:
    """
    Пайплайн адаптера:
      1) parse_markdown → ParsedDoc
      2) (если есть cfg.drop) построить интервалы удаления (sections/markers/frontmatter) и применить
         с плейсхолдерами
      3) normalize_markdown (снятие H1, max_heading_level)
      4) meta агрегируем
    """
    max_lvl = cfg.max_heading_level
    drop_cfg: MarkdownDropCfg | None = cfg.drop

    meta: dict = {
        "md.removed_h1": 0,
        "md.shifted": False,
        "md.placeholders": 0,
        "md.removed.frontmatter": False,
        "md.removed.sections": 0,
        "md.removed.markers": 0,
    }

    # 1) parse
    doc = parse_markdown(text)

    # 2) drop
    current_text = text
    if drop_cfg:
        intervals = build_drop_intervals(
            doc,
            section_rules=drop_cfg.sections,
            marker_rules=drop_cfg.markers,
            drop_frontmatter=drop_cfg.frontmatter,
        )
        # счётчики из интервалов
        if intervals:
            # грубая оценка: посчитать виды
            for _, _, m in intervals:
                k = m.get("kind")
                if k == "frontmatter":
                    meta["md.removed.frontmatter"] = True
                elif k == "section":
                    meta["md.removed.sections"] = int(meta["md.removed.sections"]) + 1
                elif k == "marker":
                    meta["md.removed.markers"] = int(meta["md.removed.markers"]) + 1
            ph_policy: PlaceholderPolicy = drop_cfg.placeholder
            current_text, ph_meta = apply_intervals_with_placeholders(doc.lines, intervals, ph_policy)
            meta.update(ph_meta)
        else:
            # нет интервалов — не перепаковываем через split/join: сохраняем исходный текст как есть
            current_text = text

    # 3) normalize (после вырезаний)
    norm_text, norm_meta = normalize_markdown(
        current_text,
        max_heading_level=max_lvl,
        group_size=group_size,
        mixed=mixed,
    )
    meta.update(norm_meta)
    return norm_text, meta
