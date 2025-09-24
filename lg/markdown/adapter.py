from __future__ import annotations

from typing import Tuple

from .intervals import build_drop_intervals
from .model import MarkdownCfg, MarkdownDropCfg, MarkdownKeepCfg, PlaceholderPolicy
from .normalize import normalize_markdown
from .parser import parse_markdown
from .transform import apply_intervals_with_placeholders


def process_markdown(text: str, cfg: MarkdownCfg, *, group_size: int, mixed: bool) -> Tuple[str, dict]:
    """
    Пайплайн адаптера:
      1) parse_markdown → ParsedDoc
      2) (если есть cfg.drop или cfg.keep) построить интервалы удаления (sections/frontmatter) и применить
         с плейсхолдерами (только в drop режиме)
      3) normalize_markdown (снятие H1, max_heading_level)
      4) meta агрегируем
    """
    max_lvl = cfg.max_heading_level
    strip_single_h1 = cfg.strip_single_h1
    drop_cfg: MarkdownDropCfg | None = cfg.drop
    keep_cfg: MarkdownKeepCfg | None = cfg.keep
    
    # Determine mode
    keep_mode = keep_cfg is not None
    
    meta: dict = {
        "md.removed_h1": 0,
        "md.shifted": False,
        "md.placeholders": 0,
        "md.removed.frontmatter": False,
        "md.removed.sections": 0,
        "md.mode": "keep" if keep_mode else "drop",
    }

    # 1) parse
    doc = parse_markdown(text)

    # 2) Process content based on mode
    current_text = text
    if drop_cfg or keep_cfg:
        # Build intervals based on appropriate config
        if keep_mode:
            intervals = build_drop_intervals(
                doc,
                section_rules=keep_cfg.sections,
                drop_frontmatter=False,  # Special handling for keep mode
                keep_mode=True,
                keep_frontmatter=keep_cfg.frontmatter,
            )
        else:
            # drop_cfg is guaranteed to be not None here
            assert drop_cfg is not None, "drop_cfg must not be None in drop mode"
            intervals = build_drop_intervals(
                doc,
                section_rules=drop_cfg.sections,
                drop_frontmatter=drop_cfg.frontmatter,
            )
            
        # Process intervals
        if intervals:
            # Count removals
            for _, _, m in intervals:
                k = m.get("kind")
                if k == "frontmatter":
                    meta["md.removed.frontmatter"] = True
                elif k in ("section", "inverse"):
                    meta["md.removed.sections"] = int(meta["md.removed.sections"]) + 1
                    
            # Apply placeholder policy (only in drop mode)
            ph_policy = PlaceholderPolicy(mode="none")
            if not keep_mode and drop_cfg is not None and drop_cfg.placeholder.mode != "none":
                ph_policy = drop_cfg.placeholder
                
            current_text, ph_meta = apply_intervals_with_placeholders(doc.lines, intervals, ph_policy)
            meta.update(ph_meta)
        else:
            # нет интервалов — не перепаковываем через split/join: сохраняем исходный текст как есть
            current_text = text

    # 3) normalize (после вырезаний)
    norm_text, norm_meta = normalize_markdown(
        current_text,
        max_heading_level=max_lvl,
        strip_single_h1=strip_single_h1,
        group_size=group_size,
        mixed=mixed,
        placeholder_inside_heading=cfg.placeholder_inside_heading,
    )
    meta.update(norm_meta)
    return norm_text, meta
