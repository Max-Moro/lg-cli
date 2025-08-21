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

    def _append_line(out: List[str], ln: str) -> None:
        """Не допускаем более двух подряд пустых строк."""
        if ln != "":
            out.append(ln)
            return
        # пустая строка
        if len(out) >= 2 and out[-1] == "" and out[-2] == "":
            return
        out.append(ln)

    def _next_live_line_is_blank(idx: int) -> bool:
        return 0 <= idx < n and lines[idx].strip() == ""

    for s, e, meta in intervals:
        s = max(0, min(s, n))
        e = max(0, min(e, n))
        if e <= s:
            continue
        # хвост до интервала
        if cur < s:
            # копируем с защитой от тройных пустых
            for ln in lines[cur:s]:
                _append_line(out_lines, ln)
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
            # минимальная нормализация шва: избегаем двойных/тройных пустых вокруг
            # если предыдущая строка пустая и следующая «живая» тоже пустая — не плодим лишнее
            prev_blank = (len(out_lines) > 0 and out_lines[-1].strip() == "")
            next_blank = _next_live_line_is_blank(e)
            if prev_blank and next_blank:
                # уже есть одна пустая сверху — просто вставим placeholder без доп. пустых
                _append_line(out_lines, ph)
            else:
                _append_line(out_lines, ph)
            placeholders += 1
        # сдвиг курсора
        cur = e

    # хвост после последнего интервала
    if cur < n:
        for ln in lines[cur:]:
            _append_line(out_lines, ln)

    return ("\n".join(out_lines), {"md.placeholders": placeholders})
