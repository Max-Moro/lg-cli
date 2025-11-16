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
            # other flags can be added as needed
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
    # Level constraints are optional
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
    Check ancestor path by exact heading texts (path = [A, B, C]):
    — Require heading to have exactly such parent chain A → B → ... (by text, no regexes).
    — If path empty/None — skip check.
    """
    if not path:
        return lambda h, all_heads: True

    def pred(h: HeadingNode, all_heads: list[HeadingNode]) -> bool:
        # Ancestor headings by titles
        parent_titles = [all_heads[i].title for i in h.parents]

        # Variant 1: path describes only ancestors (suffix of ancestor chain)
        if len(path) <= len(parent_titles):
            if parent_titles[-len(path):] == path:
                return True

        # Variant 2: path describes ancestors + current heading
        if path and path[-1] == h.title:
            need_parents = path[:-1]
            if len(need_parents) <= len(parent_titles):
                if not need_parents or parent_titles[-len(need_parents):] == need_parents:
                    return True

        return False

    return pred


def select_section_intervals(doc: ParsedDoc, rules: List[SectionRule]) -> List[tuple[int, int, SectionRule, Optional[HeadingNode]]]:
    """
    Returns list of whole section removal intervals:
      [(start_line, end_line_excl, rule, heading_or_None)]
    """
    out: list[tuple[int, int, SectionRule, Optional[HeadingNode]]] = []
    heads = doc.headings

    for rule in rules:
        # Variant 1: path only set (subtree slice of specific node with that path)
        if rule.path and not rule.match:
            # find all headings with correct parent chain and rule targeted at them
            ppred = _path_pred(rule.path)
            lpred = _level_pred(rule)
            for h in heads:
                if not ppred(h, heads):
                    continue
                if not lpred(h):
                    continue
                out.append((h.start_line, h.end_line_excl, rule, h))
            continue

        # Variant 2: match by title/slug/regex (and optionally path restriction)
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

        # if neither match nor path — rule is incorrect; just skip
    return out



