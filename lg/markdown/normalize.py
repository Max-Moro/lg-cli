from __future__ import annotations

import re
from typing import Tuple


def _strip_single_h1_if_needed(lines: list[str], group_size: int) -> Tuple[list[str], bool]:
    """
    Удаляет верхний H1 (ATX или setext) только если файл одиночный в группе.
    Возвращает (новые_строки, removed_h1_flag).
    """
    if group_size != 1 or not lines:
        return lines, False

    # ATX: "# Title"
    if re.match(r"^#\s", lines[0]):
        return lines[1:], True

    # Setext: Title + "===="
    if len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
        return lines[2:], True

    return lines, False


def normalize_markdown(text: str, *, max_heading_level: int | None, strip_single_h1: bool, group_size: int, mixed: bool) -> tuple[str, dict]:
    """
    Ровно та же семантика, что была в исходном MarkdownAdapter.process:
      • Если mixed=True или max_heading_level=None → не трогаем (кроме снятия H1).
      • Если group_size == 1 → снимаем верхний H1 (ATX/Setext).
      • Сдвиг уровней заголовков вне fenced-блоков так,
        чтобы минимальный уровень стал равен max_heading_level.
    """
    meta = {"md.removed_h1": 0, "md.shifted": False}

    lines = text.splitlines()

    # 1) снять единственный верхний H1
    if strip_single_h1:
        lines, removed_h1 = _strip_single_h1_if_needed(lines, group_size)
        if removed_h1:
            meta["md.removed_h1"] = 1

    if max_heading_level is None:
        return text, meta

    max_lvl = int(max_heading_level)

    in_fence = False
    fence_pat = re.compile(r"^```")
    head_pat = re.compile(r"^(#+)\s")
    # 2) собрать min_lvl вне fenced
    min_lvl: int | None = None
    for ln in lines:
        if fence_pat.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = head_pat.match(ln)
        if m:
            lvl = len(m.group(1))
            min_lvl = lvl if min_lvl is None else min(min_lvl, lvl)

    if min_lvl is None:
        # заголовков нет
        return ("\n".join(lines), meta)

    shift = max_lvl - min_lvl
    meta["md.shifted"] = bool(shift or removed_h1)
    if shift == 0:
        return ("\n".join(lines), meta)

    # 3) применить сдвиг вне fenced
    out: list[str] = []
    in_fence = False
    for ln in lines:
        if fence_pat.match(ln):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        m = head_pat.match(ln)
        if m:
            new_hashes = "#" * (len(m.group(1)) + shift)
            out.append(f"{new_hashes} {ln[m.end():]}")
        else:
            out.append(ln)

    return ("\n".join(out), meta)
