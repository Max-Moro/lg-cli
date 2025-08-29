from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List

from .common import TemplateTokens, parse_locator, load_from_cfg, CTX_SUFFIX, TPL_SUFFIX
from ..types import ContextSpec, CanonSectionId


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


@dataclass(frozen=True)
class ComposedDocument:
    """
    Итог композиции контекста:
      • text — финальный документ (клей-шаблоны + вставки секций)
      • sections_only_text — тот же документ, но без «клея» (только вставки секций)
      • templates_hashes — карта { '<cfg_root>::{ctx|tpl}:<name>' → sha1(исходного текста) }
    """
    text: str
    sections_only_text: str
    templates_hashes: Dict[str, str]


def _load_doc_text(kind: str, cfg_root_current: Path, name: str) -> Tuple[Path, str, str]:
    """
    Загрузка текста документа (tpl/ctx) и ключ для templates_hashes.
    Возвращает (path, src, key).
    """
    suffix = TPL_SUFFIX if kind == "tpl" else CTX_SUFFIX
    p, src = load_from_cfg(cfg_root_current, name, suffix=suffix)
    key = f"{cfg_root_current.as_posix()}::{kind}:{name}"
    return p, src, key


def compose_context(
    repo_root: Path,
    base_cfg_root: Path,
    spec: ContextSpec,
    rendered_by_section: Dict[CanonSectionId, str],
    ph2canon: Dict[str, CanonSectionId],
) -> ComposedDocument:
    """
    Собирает итоговый документ по ContextSpec:
      • kind="section": возвращает рендер одной секции;
      • kind="context": раскрывает документ ctx + вложенные tpl/ctx, подставляет секции.
    """

    def _expand(kind: str, name: str, current_cfg_root: Path, templates: Dict[str, str],
                stack: List[Tuple[Path, str]] | None = None) -> Tuple[str, str]:
        """
        Универсальный расширитель tpl/ctx.
        Возвращает (final_text, sections_only_text).
        """
        _stack = stack or []
        marker = (current_cfg_root, f"{kind}:{name}")
        if marker in _stack:
            cycle = " → ".join([f"{p.as_posix()}::{n}" for p, n in _stack] + [f"{current_cfg_root.as_posix()}::{kind}:{name}"])
            raise RuntimeError(f"{kind.upper()} cycle detected: {cycle}")

        _p, src, hkey = _load_doc_text(kind, current_cfg_root, name)
        templates[hkey] = _sha1(src)
        _stack.append(marker)

        out_final_parts: list[str] = []
        out_sections_only_parts: list[str] = []
        pos = 0

        for m in TemplateTokens.iter_matches(src):
            start, end = m.span()
            # Литерал между плейсхолдерами — только в финальный текст
            if start > pos:
                out_final_parts.append(src[pos:start])

            ph = m.group("braced") or m.group("name") or ""
            if ph.startswith("tpl:"):
                child = ph[4:]
                child_final, child_sections_only = _expand("tpl", child, current_cfg_root, templates, _stack)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            elif ph.startswith("tpl@"):
                loc = parse_locator(ph, expected_kind="tpl")
                child_cfg_root = (repo_root / loc.origin / "lg-cfg").resolve() if loc.origin != "self" else current_cfg_root
                child_final, child_sections_only = _expand("tpl", loc.resource, child_cfg_root, templates, _stack)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            elif ph.startswith("ctx:"):
                child = ph[4:]
                child_final, child_sections_only = _expand("ctx", child, current_cfg_root, templates, _stack)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            elif ph.startswith("ctx@"):
                loc = parse_locator(ph, expected_kind="ctx")
                child_cfg_root = (repo_root / loc.origin / "lg-cfg").resolve() if loc.origin != "self" else current_cfg_root
                child_final, child_sections_only = _expand("ctx", loc.resource, child_cfg_root, templates, _stack)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)

            else:
                # Секция: ключуем по канону
                canon = ph2canon.get(ph)
                if not canon:
                    raise RuntimeError(
                        f"Unknown section placeholder '{ph}' during composition "
                        f"(no canon mapping). Ensure resolver collected it from templates/contexts."
                    )
                sec_text = rendered_by_section.get(canon, "")
                out_final_parts.append(sec_text)
                out_sections_only_parts.append(sec_text)

            pos = end

        # Хвостовой литерал
        if pos < len(src):
            out_final_parts.append(src[pos:])

        _stack.pop()
        return "".join(out_final_parts), "".join(out_sections_only_parts)

    if spec.kind == "section":
        canon = spec.section_refs[0].canon
        sec_text = rendered_by_section.get(canon, "")
        return ComposedDocument(text=sec_text, sections_only_text=sec_text, templates_hashes={})

    # Контекст: раскрываем через общий расширитель
    templates_hashes: Dict[str, str] = {}
    final_text, sections_only = _expand("ctx", spec.name, base_cfg_root, templates_hashes, stack=[])

    return ComposedDocument(text=final_text, sections_only_text=sections_only, templates_hashes=templates_hashes)
