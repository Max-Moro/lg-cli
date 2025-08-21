from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .resolver import _template_path, _Template
from ..types import ContextSpec


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


@dataclass(frozen=True)
class ComposedDocument:
    """
    Итог композиции контекста:
      • text — финальный документ (клей-шаблоны + вставки секций)
      • sections_only_text — тот же документ, но без «клея» (чистые вставки секций в порядке появления)
      • templates_hashes — карта {имя шаблона → sha1(его исходного текста)}
    """
    text: str
    sections_only_text: str
    templates_hashes: Dict[str, str]


def compose_context(root: Path, spec: ContextSpec, rendered_by_section: Dict[str, str]) -> ComposedDocument:
    """
    Собирает итоговый документ по ContextSpec:
      - для kind="section": возвращает рендер секции;
      - для kind="context": раскрывает шаблон и вложенные ${tpl:...}, подставляет секции.
    """

    def _load_template(name: str) -> str:
        p = _template_path(root, name)
        return p.read_text(encoding="utf-8", errors="ignore")

    def _expand(name: str, templates: Dict[str, str]) -> Tuple[str, str]:
        """
        Рекурсивно расширяет один шаблон.
        Возвращает (final_text, sections_only_text).
        """
        src = _load_template(name)
        templates[name] = _sha1(src)

        # Проходим по плейсхолдерам в порядке появления, собирая текст.
        out_final_parts: list[str] = []
        out_sections_only_parts: list[str] = []
        pos = 0
        for m in _Template.pattern.finditer(src):
            start, end = m.span()
            # Литерал до плейсхолдера — это "клей": идёт только в финальный текст
            if start > pos:
                out_final_parts.append(src[pos:start])
            ph = m.group("braced") or m.group("name") or ""
            if ph.startswith("tpl:"):
                # Вложенный шаблон
                child = ph[4:]
                child_final, child_sections_only = _expand(child, templates)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)
            else:
                # Секция
                sec_text = rendered_by_section.get(ph, "")
                out_final_parts.append(sec_text)
                out_sections_only_parts.append(sec_text)
            pos = end

        # Хвостовой литерал (клей)
        if pos < len(src):
            out_final_parts.append(src[pos:])

        return "".join(out_final_parts), "".join(out_sections_only_parts)

    if spec.kind == "section":
        sec_text = rendered_by_section.get(spec.name, "")
        return ComposedDocument(text=sec_text, sections_only_text=sec_text, templates_hashes={})

    templates_hashes: Dict[str, str] = {}
    final_text, sections_only = _expand(spec.name, templates_hashes)

    return ComposedDocument(text=final_text, sections_only_text=sections_only, templates_hashes=templates_hashes)
