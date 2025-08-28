from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .common import TemplateTokens, parse_tpl_locator, load_template_from, load_context_text
from ..types import ContextSpec


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


@dataclass(frozen=True)
class ComposedDocument:
    """
    Итог композиции контекста:
      • text — финальный документ (клей-шаблоны + вставки секций)
      • sections_only_text — тот же документ, но без «клея» (только вставки секций)
      • templates_hashes — карта { '<cfg_root>::<name>' → sha1(исходного текста) }
    """
    text: str
    sections_only_text: str
    templates_hashes: Dict[str, str]


def compose_context(
    repo_root: Path,
    base_cfg_root: Path,
    spec: ContextSpec,
    rendered_by_section: Dict[str, str],
) -> ComposedDocument:
    """
    Собирает итоговый документ по ContextSpec:
      • kind="section": возвращает рендер одной секции;
      • kind="context": раскрывает шаблон и вложенные ${tpl:...}/${tpl@...:...}, подставляет секции.
    """

    def _expand_template(name: str, current_cfg_root: Path, templates: Dict[str, str]) -> Tuple[str, str]:
        """
        Рекурсивно расширяет один ШАБЛОН (.tpl.md) относительно current_cfg_root.
        Возвращает (final_text, sections_only_text).
        """
        _p, src = load_template_from(current_cfg_root, name)
        templates[f"{current_cfg_root.as_posix()}::{name}"] = _sha1(src)

        out_final_parts: list[str] = []
        out_sections_only_parts: list[str] = []
        pos = 0

        for m in TemplateTokens.iter_matches(src):
            start, end = m.span()
            # Литерал до плейсхолдера — идёт только в финальный текст
            if start > pos:
                out_final_parts.append(src[pos:start])

            ph = m.group("braced") or m.group("name") or ""
            if ph.startswith("tpl:"):
                child = ph[4:]
                child_final, child_sections_only = _expand_template(child, current_cfg_root, templates)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            elif ph.startswith("tpl@"):
                child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=current_cfg_root, repo_root=repo_root)
                child_final, child_sections_only = _expand_template(child_name, child_cfg_root, templates)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            else:
                # Секция
                sec_text = rendered_by_section.get(ph, "")
                out_final_parts.append(sec_text)
                out_sections_only_parts.append(sec_text)

            pos = end

        # Хвостовой литерал
        if pos < len(src):
            out_final_parts.append(src[pos:])

        return "".join(out_final_parts), "".join(out_sections_only_parts)

    if spec.kind == "section":
        sec_text = rendered_by_section.get(spec.name, "")
        return ComposedDocument(text=sec_text, sections_only_text=sec_text, templates_hashes={})

    # Контекст: читаем корневой .ctx.md (всегда из self cfg-root)
    ctx_src = load_context_text(repo_root, spec.name)

    templates_hashes: Dict[str, str] = {}
    templates_hashes[f"{base_cfg_root.as_posix()}::ctx:{spec.name}"] = _sha1(ctx_src)

    out_final_parts: list[str] = []
    out_sections_only_parts: list[str] = []
    pos = 0

    for m in TemplateTokens.iter_matches(ctx_src):
        start, end = m.span()
        if start > pos:
            out_final_parts.append(ctx_src[pos:start])

        ph = m.group("braced") or m.group("name") or ""
        if ph.startswith("tpl:"):
            child = ph[4:]
            child_final, child_sections_only = _expand_template(child, base_cfg_root, templates_hashes)
            out_final_parts.append(child_final)
            out_sections_only_parts.append(child_sections_only)

        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = parse_tpl_locator(ph, current_cfg_root=base_cfg_root, repo_root=repo_root)
            child_final, child_sections_only = _expand_template(child_name, child_cfg_root, templates_hashes)
            out_final_parts.append(child_final)
            out_sections_only_parts.append(child_sections_only)

        else:
            sec_text = rendered_by_section.get(ph, "")
            out_final_parts.append(sec_text)
            out_sections_only_parts.append(sec_text)

        pos = end

    if pos < len(ctx_src):
        out_final_parts.append(ctx_src[pos:])

    final_text = "".join(out_final_parts)
    sections_only = "".join(out_sections_only_parts)

    return ComposedDocument(text=final_text, sections_only_text=sections_only, templates_hashes=templates_hashes)
