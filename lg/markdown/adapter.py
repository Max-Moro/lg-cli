from __future__ import annotations

from typing import List, Tuple

from .intervals import build_drop_intervals
from .model import MarkdownCfg, MarkdownDropCfg, MarkdownKeepCfg, PlaceholderPolicy, ParsedDoc, SectionRule
from .normalize import normalize_markdown
from .parser import parse_markdown
from .selectors import select_section_intervals
from .transform import apply_intervals_with_placeholders


def process_markdown(text: str, cfg: MarkdownCfg, file_label: str) -> Tuple[str, dict]:
    """
    Пайплайн адаптера:
      1) parse_markdown → ParsedDoc
      2) (если есть cfg.drop или cfg.keep) построить интервалы удаления (sections/frontmatter) и применить
         с плейсхолдерами (только в drop режиме)
      3) normalize_markdown (снятие H1 если strip_h1=True, max_heading_level)
      4) meta агрегируем
    """
    max_lvl = cfg.max_heading_level
    strip_h1 = cfg.strip_h1
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
            # Validate anchor links in keep mode
            _validate_anchor_sections_found(doc, keep_cfg.sections, intervals)
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
        strip_h1=strip_h1,
        file_label=file_label,
        placeholder_inside_heading=cfg.placeholder_inside_heading
    )
    meta.update(norm_meta)
    return norm_text, meta


def _validate_anchor_sections_found(doc: ParsedDoc, section_rules: List[SectionRule], intervals: list) -> None:
    """
    Валидирует что все якорные ссылки найдены в документе.
    Для keep-режима проверяет что каждое правило нашло хотя бы один заголовок.

    Args:
        doc: Разобранный документ
        section_rules: Список правил для поиска секций
        intervals: Интервалы которые были найдены

    Raises:
        RuntimeError: Если якорь не найден в документе
    """
    if not section_rules:
        return

    # Проверяем каждое правило индивидуально
    for rule in section_rules:
        # Проверяем есть ли правило с anchor-подсказкой в reason
        if rule.reason and "md placeholder anchor:" in rule.reason:
            # Находим все интервалы которые создало это правило
            rule_intervals = select_section_intervals(doc, [rule])

            if not rule_intervals:
                # Извлекаем информацию об якоре из reason
                import re
                anchor_match = re.search(r'md placeholder anchor: #([^(]+)', rule.reason)
                anchor_name = anchor_match.group(1).strip() if anchor_match else "unknown"

                # Собираем список доступных заголовков для диагностики
                available_headings = [h.title for h in doc.headings] if doc.headings else []

                if available_headings:
                    error_msg = (
                        f"Anchor section '#{anchor_name}' not found in markdown document. "
                        f"Available sections: {', '.join(available_headings[:5])}{'...' if len(available_headings) > 5 else ''}"
                    )
                else:
                    error_msg = f"Anchor section '#{anchor_name}' not found - document has no sections"

                raise RuntimeError(error_msg)
