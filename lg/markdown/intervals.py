from __future__ import annotations

from typing import List, Optional, Tuple

from .model import SectionRule, MarkerRule, ParsedDoc
from .selectors import select_section_intervals, select_marker_intervals


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
    for s, e, m in intervals[1:]:
        if s <= cur_e:  # перекрытие или касание
            # extend
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
                        cur_meta[k] = v
        else:
            merged.append((cur_s, cur_e, cur_meta))
            cur_s, cur_e, cur_meta = s, e, m
    merged.append((cur_s, cur_e, cur_meta))
    return merged


def build_drop_intervals(doc: ParsedDoc, *, section_rules: List[SectionRule], marker_rules: List[MarkerRule], drop_frontmatter: bool) -> List[Interval]:
    """
    Строит итоговый, слитый список интервалов для удаления.
    payload_meta содержит:
      • kind: "section" | "marker" | "frontmatter"
      • title, level, reason (когда применимо)
      • placeholders: {template_override?}
    """
    intervals: List[Interval] = []

    # 1) Секции
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

    # 2) Маркеры
    mints = select_marker_intervals(doc.lines, marker_rules)
    for s, e, rule in mints:
        meta = {
            "kind": "marker",
            "title": None,
            "level": None,
            "reason": rule.reason,
            "placeholder": rule.placeholder or None,
            "count": 1,
        }
        intervals.append((s, e, meta))

    # 3) Frontmatter
    if drop_frontmatter and doc.frontmatter_range:
        s, e = doc.frontmatter_range
        intervals.append((s, e, {"kind": "frontmatter", "title": None, "level": None, "reason": "frontmatter", "placeholder": None, "count": 1}))

    # 4) Слияние
    return _merge_intervals(intervals)
