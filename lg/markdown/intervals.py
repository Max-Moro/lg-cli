from __future__ import annotations

from typing import List, Tuple

from .model import SectionRule, ParsedDoc
from .selectors import select_section_intervals

Interval = Tuple[int, int, dict]  # (start, end_excl, payload_meta)


def _merge_intervals(intervals: List[Interval]) -> List[Interval]:
    """
    Слияние перекрывающихся и соприкасающихся интервалов.
    Политика: объединяем, payload метаданные агрегируем (суммарно).
    """
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: List[Interval] = []
    cur_s, cur_e, cur_meta = intervals[0]
    # трекаем лучший источник placeholder/reason по ширине
    best_width = max(0, cur_e - cur_s)
    best_placeholder = cur_meta.get("placeholder") if isinstance(cur_meta, dict) else None
    best_reason = cur_meta.get("reason") if isinstance(cur_meta, dict) else None
    for s, e, m in intervals[1:]:
        if s <= cur_e:  # перекрытие или касание
            # extend границу
            if e > cur_e:
                cur_e = e
            # агрегируем счётчики
            for k, v in m.items():
                if isinstance(v, int):
                    cur_meta[k] = int(cur_meta.get(k, 0)) + v
                else:
                    # списки/строки можем аккумулировать в списки
                    if isinstance(v, list):
                        cur_meta[k] = list(cur_meta.get(k, [])) + v
                    else:
                        # по умолчанию — сохраняем предыдущее (стабильно),
                        # т.к. placeholder/reason выберем отдельной логикой.
                        cur_meta.setdefault(k, v)
            # политика выбора placeholder/reason: от самого широкого интервала,
            # при равной ширине — из более раннего (т.е. оставляем текущий).
            width_now = e - s
            if width_now > best_width:
                best_width = width_now
                best_placeholder = m.get("placeholder")
                best_reason = m.get("reason")
        else:
            # финализируем placeholder/reason для собранного окна
            if isinstance(cur_meta, dict):
                if best_placeholder is not None:
                    cur_meta["placeholder"] = best_placeholder
                if best_reason is not None:
                    cur_meta["reason"] = best_reason
            merged.append((cur_s, cur_e, cur_meta))
            cur_s, cur_e, cur_meta = s, e, m
            best_width = max(0, e - s)
            best_placeholder = m.get("placeholder")
            best_reason = m.get("reason")
    # финализируем хвост
    if isinstance(cur_meta, dict):
        if best_placeholder is not None:
            cur_meta["placeholder"] = best_placeholder
        if best_reason is not None:
            cur_meta["reason"] = best_reason
    merged.append((cur_s, cur_e, cur_meta))
    return merged


def invert_intervals(keep_intervals: List[Interval], doc_length: int) -> List[Interval]:
    """
    Converts intervals to keep into intervals to drop (inverse operation).
    
    Args:
        keep_intervals: Intervals to preserve
        doc_length: Total length of document (in lines)
        
    Returns:
        List of intervals to drop
    """
    if not keep_intervals:
        # If no keep intervals, drop everything
        return [(0, doc_length, {"kind": "inverse", "reason": "keep_mode_drop_all", "count": 1})]
        
    # Sort and merge overlapping intervals first
    keep_intervals = _merge_intervals(keep_intervals)
    
    # Build drop intervals (everything not in keep intervals)
    drop_intervals = []
    current_pos = 0
    
    for start, end, meta in keep_intervals:
        if current_pos < start:
            # Add a drop interval for the gap
            drop_intervals.append((
                current_pos, 
                start, 
                {"kind": "inverse", "reason": "keep_mode_inversion", "count": 1}
            ))
        current_pos = max(current_pos, end)
    
    # Add final interval if needed
    if current_pos < doc_length:
        drop_intervals.append((
            current_pos,
            doc_length,
            {"kind": "inverse", "reason": "keep_mode_inversion", "count": 1}
        ))
    
    return drop_intervals


def build_drop_intervals(
    doc: ParsedDoc, 
    *, 
    section_rules: List[SectionRule] | None = None,
    drop_frontmatter: bool = False,
    keep_mode: bool = False,
    keep_frontmatter: bool = False,
) -> List[Interval]:
    """
    Строит итоговый, слитый список интервалов для удаления.
    В режиме keep_mode=True строит интервалы для сохранения, а затем инвертирует их.
    payload_meta содержит:
      • kind: "section" | "frontmatter" | "inverse"
      • title, level, reason (когда применимо)
      • placeholders: {template_override?}
    """
    if keep_mode and section_rules is None:
        section_rules = []
        
    intervals: List[Interval] = []

    # 1) Секции
    if section_rules:
        for s, e, rule, h in select_section_intervals(doc, section_rules):
            meta = {
                "kind": "section",
                "title": (h.title if h else None),
                "level": (h.level if h else None),
                "reason": rule.reason,
                "placeholder": rule.placeholder or None,
                "count": 1,
            }
            intervals.append((s, e, meta))

    # 2) Frontmatter - handle based on mode
    if doc.frontmatter_range:
        s, e = doc.frontmatter_range
        # In drop mode: add frontmatter to intervals if drop_frontmatter=True
        # In keep mode: add frontmatter to intervals if keep_frontmatter=True
        if (not keep_mode and drop_frontmatter) or (keep_mode and keep_frontmatter):
            intervals.append((
                s, e, 
                {
                    "kind": "frontmatter", 
                    "title": None, 
                    "level": None, 
                    "reason": "frontmatter", 
                    "placeholder": None, 
                    "count": 1
                }
            ))

    # 3) In keep mode, invert the intervals
    if keep_mode:
        return invert_intervals(intervals, doc.line_count())
        
    # 4) Слияние
    return _merge_intervals(intervals)
