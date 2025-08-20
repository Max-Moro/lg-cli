from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .model import ParsedDoc, HeadingNode
from .slug import slugify_github

_ATX = re.compile(r"^(?P<indent>[ ]{0,3})(?P<marks>#{1,6})[ \t]+(?P<title>.+?)\s*$")
_SETEXT_U = re.compile(r"^(?P<underline>={2,})\s*$")
_SETEXT_L = re.compile(r"^(?P<underline>-{2,})\s*$")
_FENCE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<lang>[A-Za-z0-9_\-+]*)")
_FRONTMATTER_LINE = re.compile(r"^ {0,3}-{3,}\s*$")


def _scan_fenced(lines: List[str]) -> List[Tuple[int, int]]:
    """Возвращает интервалы fenced-блоков [start, end_excl]."""
    out: List[Tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        open_marks = m.group("fence")              # e.g. "```" or "~~~~"
        tick = open_marks[0]                       # '`' or '~'
        need = len(open_marks)                     # minimal closing length
        # Closing fence: same char, at least `need` times, optional trailing spaces.
        fence_pat = re.compile(rf"^(?: {{0,3}}){re.escape(tick)}{{{need},}}[ \t]*$")
        start = i
        i += 1
        while i < n and not fence_pat.match(lines[i]):
            i += 1
        if i < n:
            end = i + 1
            out.append((start, end))
            i = end
        else:
            # незакрытый блок — считаем до конца
            out.append((start, n))
            break
    return out


def _in_any_range(i: int, ranges: List[Tuple[int, int]]) -> bool:
    for a, b in ranges:
        if a <= i < b:
            return True
    return False


def _scan_frontmatter(lines: List[str], fenced: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """
    YAML front matter — только если начинается с первой строки и не внутри fenced.
    Ищем:
      ---...\n   (3+ дефисов, допускается отступ до 3 пробелов)
      ...\n
      ---...\n   (закрывающая полоса из дефисов)
    Удаляем БЛОК ПОЛНОСТЬЮ (включая обе полосы) и дополнительно
    проглатываем последующие пустые строки после закрывающей полосы.
    Возвращаем (start=0, end_excl) — индекс первой строки ПОСЛЕ всего блока.
    """
    if not lines:
        return None
    if not _FRONTMATTER_LINE.match(lines[0]):
        return None
    # Найдём закрывающую '---' далее, не попав в fenced
    i = 1
    n = len(lines)
    while i < n:
        if _in_any_range(i, fenced):
            # если внезапно fenced начался раньше закрытия — прекращаем (невалидный фронтматтер)
            return None
        if _FRONTMATTER_LINE.match(lines[i]):
            # включаем закрывающую полосу
            end_excl = i + 1
            # проглатываем последующие пустые строки
            while end_excl < n and not lines[end_excl].strip():
                end_excl += 1
            return (0, end_excl)
        i += 1
    return None


def parse_markdown(text: str) -> ParsedDoc:
    """
    Лёгкий парсер Markdown:
      • fenced-блоки (``` / ~~~)
      • заголовки ATX (#..######) и Setext (====/----)
      • YAML front matter
    """
    lines = text.splitlines()
    fenced = _scan_fenced(lines)
    front = _scan_frontmatter(lines, fenced)

    headings: List[HeadingNode] = []

    # Скан ATX-заголовков (игнорируем строки внутри fenced)
    for i, ln in enumerate(lines):
        if _in_any_range(i, fenced):
            continue
        m = _ATX.match(ln)
        if m:
            level = len(m.group("marks"))
            title = m.group("title").strip()
            slug = slugify_github(title)
            headings.append(HeadingNode(level=level, title=title, slug=slug,
                                        start_line=i, end_line_excl=-1, parents=[]))

    # Скан Setext: строка X + следующая линия ==== или ---- (не внутри fenced)
    i = 0
    n = len(lines)
    while i + 1 < n:
        if _in_any_range(i, fenced) or _in_any_range(i + 1, fenced):
            i += 1
            continue
        title_line = lines[i]
        under = lines[i + 1]
        if _SETEXT_U.match(under) or _SETEXT_L.match(under):
            # Уровень: '=' → 1, '-' → 2
            level = 1 if _SETEXT_U.match(under) else 2
            title = title_line.strip()
            if title:  # пустой заголовок не учитываем
                slug = slugify_github(title)
                headings.append(HeadingNode(level=level, title=title, slug=slug,
                                            start_line=i, end_line_excl=-1, parents=[]))
            i += 2
        else:
            i += 1

    # Отсортировать по порядку появления
    headings.sort(key=lambda h: h.start_line)

    # Посчитать границы поддеревьев и родителей (стек уровней)
    stack: List[int] = []  # индексы headings
    for idx, h in enumerate(headings):
        # поп пока верхний уровень >= текущего
        while stack and headings[stack[-1]].level >= h.level:
            top = stack.pop()
            # end_line_excl для завершённых позже поставим, когда узнаем start следующего
        # родители = копия стека
        h.parents = list(stack)
        stack.append(idx)

    # end_line_excl: ближайший следующий с уровнем <=, иначе до конца документа
    for i, h in enumerate(headings):
        # найти следующий заголовок j > i с level <= h.level
        end = len(lines)
        for j in range(i + 1, len(headings)):
            if headings[j].level <= h.level:
                end = headings[j].start_line
                break
        h.end_line_excl = end

    return ParsedDoc(lines=lines, headings=headings, fenced_ranges=fenced, frontmatter_range=front)
