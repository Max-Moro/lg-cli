from __future__ import annotations

from typing import List

from .model import PlaceholderPolicy
from .placeholders import render_placeholder


def apply_intervals_with_placeholders(lines: List[str], intervals: List[tuple[int, int, dict]], policy: PlaceholderPolicy) -> tuple[str, dict]:
    """
    Применяет непересекающиеся интервалы удаления к lines и вставляет плейсхолдеры.
    Возвращает (text, meta).
    """
    if not intervals:
        return ("\n".join(lines), {"md.placeholders": 0})

    # intervals считаем уже слитыми и отсортированными
    out_lines: List[str] = []
    cur = 0
    placeholders = 0

    n = len(lines)
    for s, e, meta in intervals:
        s = max(0, min(s, n))
        e = max(0, min(e, n))
        if e <= s:
            continue
        # хвост до интервала
        if cur < s:
            out_lines.extend(lines[cur:s])
        # метрики
        removed_lines = e - s
        removed_bytes = sum(len(l) + 1 for l in lines[s:e])  # +1 за "\n" примерно
        # плейсхолдер
        ph = render_placeholder(
            removed_lines, removed_bytes,
            title=meta.get("title") if isinstance(meta, dict) else None,
            policy=policy,
            override_template=meta.get("placeholder") if isinstance(meta, dict) else None,
        )
        if ph:
            out_lines.append(ph)
            placeholders += 1
        # сдвиг курсора
        cur = e

    # хвост после последнего интервала
    if cur < n:
        out_lines.extend(lines[cur:])

    return ("\n".join(out_lines), {"md.placeholders": placeholders})
