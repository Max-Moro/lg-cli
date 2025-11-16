from __future__ import annotations

import re
from typing import List

from .model import PlaceholderPolicy
from .placeholders import render_placeholder


def apply_intervals_with_placeholders(lines: List[str], intervals: List[tuple[int, int, dict]], policy: PlaceholderPolicy) -> tuple[str, dict]:
    """
    Apply non-overlapping removal intervals to lines and insert placeholders.
    Returns (text, meta).
    """
    if not intervals:
        return "\n".join(lines), {"md.placeholders": 0}

    # intervals are already merged and sorted
    out_lines: List[str] = []
    cur = 0
    placeholders = 0

    n = len(lines)

    def _append_line(out: List[str], ln: str) -> None:
        """Don't allow more than two consecutive blank lines."""
        if ln != "":
            out.append(ln)
            return
        # blank line
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
        # tail before interval
        if cur < s:
            # copy with protection from triple blanks
            for ln in lines[cur:s]:
                _append_line(out_lines, ln)
        # metrics
        removed_lines = e - s
        removed_bytes = sum(len(l) + 1 for l in lines[s:e])  # +1 for "\n" approx
        # placeholder
        ph = render_placeholder(
            removed_lines, removed_bytes,
            title=meta.get("title") if isinstance(meta, dict) else None,
            level=meta.get("level") if isinstance(meta, dict) else None,
            policy=policy,
            override_template=meta.get("placeholder") if isinstance(meta, dict) else None,
        )
        if ph:
            # minimal seam normalization: avoid double/triple blanks around
            # if previous line blank and next "live" also blank — don't create extra
            prev_blank = (len(out_lines) > 0 and out_lines[-1].strip() == "")
            next_blank = _next_live_line_is_blank(e)
            if prev_blank and next_blank:
                # already have one blank above — just insert placeholder without extras
                _append_line(out_lines, ph)
            else:
                _append_line(out_lines, ph)
            placeholders += 1
        # cursor shift
        cur = e

    # tail after last interval
    if cur < n:
        for ln in lines[cur:]:
            _append_line(out_lines, ln)

    # Assembly and final normalization: don't allow 3+ consecutive blank lines.
    text = "\n".join(out_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, {"md.placeholders": placeholders}
