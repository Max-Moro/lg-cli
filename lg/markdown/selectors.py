from __future__ import annotations

import re
from typing import Callable, List, Optional

from .model import (
    SectionMatch, SectionRule, HeadingNode, ParsedDoc
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
        # Заголовки предков по титулам
        parent_titles = [all_heads[i].title for i in h.parents]

        # Вариант 1: path описывает только предков (суффикс цепочки предков)
        if len(path) <= len(parent_titles):
            if parent_titles[-len(path):] == path:
                return True

        # Вариант 2: path описывает предков + текущий заголовок
        if path and path[-1] == h.title:
            need_parents = path[:-1]
            if len(need_parents) <= len(parent_titles):
                if not need_parents or parent_titles[-len(need_parents):] == need_parents:
                    return True

        return False

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



