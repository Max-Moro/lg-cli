from __future__ import annotations

import re
from typing import Callable, Iterable, List, Optional

from .model import (
    SectionMatch, SectionRule, MarkerRule, PlaceholderPolicy,
    MarkdownDropCfg, MarkdownCfg, HeadingNode, ParsedDoc
)
from .slug import slugify_github


def _compile_regex(pattern: str, flags: str | None) -> re.Pattern:
    fl = 0
    if flags:
        for ch in flags:
            if ch == "i":
                fl |= re.IGNORECASE
            elif ch == "m":
                fl |= re.MULTILINE
            elif ch == "s":
                fl |= re.DOTALL
            # другие флаги можно добавить при необходимости
    return re.compile(pattern, fl)


def _title_matcher(sm: SectionMatch) -> Callable[[HeadingNode], bool]:
    kind = sm.kind
    if kind == "text":
        target = sm.pattern
        return lambda h: h.title == target
    if kind == "slug":
        pat = sm.pattern
        return lambda h: slugify_github(h.title) == pat
    if kind == "regex":
        rx = _compile_regex(sm.pattern, sm.flags)
        return lambda h: bool(rx.search(h.title))
    raise ValueError(f"Unknown match kind: {kind}")


def _level_pred(rule: SectionRule) -> Callable[[HeadingNode], bool]:
    # Ограничители уровней опциональны
    le = rule.level_exact
    leq = rule.level_at_most
    geq = rule.level_at_least

    def ok(h: HeadingNode) -> bool:
        if le is not None and h.level != le:
            return False
        if leq is not None and h.level > leq:
            return False
        if geq is not None and h.level < geq:
            return False
        return True

    return ok


def _path_pred(path: list[str] | None) -> Callable[[HeadingNode, list[HeadingNode]], bool]:
    """
    Проверка пути предков по точным текстам заголовков (path = [A, B, C]):
    — Требуем, чтобы заголовок имел ровно такую цепочку родителя A → B → ... (по текстам, без регекспов).
    — Если path пуст/None — пропускаем проверку.
    """
    if not path:
        return lambda h, all_heads: True

    def pred(h: HeadingNode, all_heads: list[HeadingNode]) -> bool:
        if len(h.parents) < len(path):
            return False
        # Возьмём хвост соответствующей длины
        parent_indices = h.parents[-len(path):] if path else []
        titles = [all_heads[i].title for i in parent_indices]
        return titles == path

    return pred


def select_section_intervals(doc: ParsedDoc, rules: List[SectionRule]) -> List[tuple[int, int, SectionRule, Optional[HeadingNode]]]:
    """
    Возвращает список интервалов удаления целых разделов:
      [(start_line, end_line_excl, rule, heading_or_None)]
    """
    out: list[tuple[int, int, SectionRule, Optional[HeadingNode]]] = []
    heads = doc.headings

    for rule in rules:
        # Вариант 1: задан path только (срез поддерева конкретного узла с таким путём)
        if rule.path and not rule.match:
            # найдём все заголовки, у которых цепочка родителей ок и на которые правило нацелено
            ppred = _path_pred(rule.path)
            lpred = _level_pred(rule)
            for h in heads:
                if not ppred(h, heads):
                    continue
                if not lpred(h):
                    continue
                out.append((h.start_line, h.end_line_excl, rule, h))
            continue

        # Вариант 2: match по title/slug/regex (и опционально path-ограничение)
        if rule.match:
            tpred = _title_matcher(rule.match)
            ppred = _path_pred(rule.path)
            lpred = _level_pred(rule)
            for h in heads:
                if not tpred(h):
                    continue
                if not ppred(h, heads):
                    continue
                if not lpred(h):
                    continue
                out.append((h.start_line, h.end_line_excl, rule, h))
            continue

        # если ни match, ни path — правило некорректно; просто пропускаем
    return out


def select_marker_intervals(lines: List[str], markers: List[MarkerRule]) -> List[tuple[int, int, MarkerRule]]:
    """
    Для каждого маркерного правила ищем непересекающиеся пары start-end по порядку.
    Если end не найден — считаем до конца файла.
    """
    out: list[tuple[int, int, MarkerRule]] = []
    n = len(lines)
    def _find_line(target: str, start_idx: int) -> int:
        """Ищем строку сначала по точному равенству, затем по .strip()."""
        t_exact = target
        t_stripped = target.strip()
        # точное совпадение
        for j in range(start_idx, n):
            if lines[j] == t_exact:
                return j
        # сравнение по .strip()
        for j in range(start_idx, n):
            if lines[j].strip() == t_stripped:
                return j
        return -1

    for rule in markers:
        i = 0
        while i < n:
            # поиск start (exact → strip)
            s = _find_line(rule.start, i)
            if s < 0:
                break
            # поиск end (exact → strip)
            e = _find_line(rule.end, s + 1)
            end_excl = (e + 1) if e >= 0 else n
            # интервал
            if not rule.include_markers:
                s0 = s + 1
                e0 = end_excl - 1 if end_excl > s + 1 else s + 1
                out.append((s0, e0, rule))
            else:
                out.append((s, end_excl, rule))
            i = end_excl
    return out
