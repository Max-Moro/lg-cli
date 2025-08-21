from __future__ import annotations

import re

import unicodedata

_slug_ws = re.compile(r"\s+")
_slug_keep = re.compile(r"[^a-z0-9\-]+")

def slugify_github(title: str) -> str:
    """
    Примерно GitHub-style slug:
      • NFKD нормализация, lower
      • пробелы → '-'
      • убрать пунктуацию, кроме '-'
      • сжать повторяющиеся '-'
      • обрезать по краям
    """
    t = unicodedata.normalize("NFKD", title).lower()
    t = _slug_ws.sub("-", t.strip())
    t = _slug_keep.sub("", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t
