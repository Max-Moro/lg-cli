from __future__ import annotations

from typing import Optional

from .model import PlaceholderPolicy


def render_placeholder(
    lines_removed: int,
    bytes_removed: int,
    *,
    title: Optional[str],
    level: Optional[int],
    policy: PlaceholderPolicy,
    override_template: str | None,
) -> str:
    """
    Returns a single placeholder line (without trailing \n).
    """
    if policy.mode == "none":
        return ""  # don't insert anything

    template = (override_template or policy.template or "> *(omitted)*").strip()
    # Simple substitution, without format specs:
    def _fmt(s: str) -> str:
        s = s.replace("{title}", title or "section")
        s = s.replace("{lines}", str(lines_removed))
        s = s.replace("{bytes}", str(bytes_removed))
        s = s.replace("{level}", "" if level is None else str(level))
        return s

    return _fmt(template)
