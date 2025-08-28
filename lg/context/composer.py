from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .resolver import _Template
from ..config.paths import context_path
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


def compose_context(repo_root: Path, base_cfg_root: Path, spec: ContextSpec, rendered_by_section: Dict[str, str]) -> ComposedDocument:
    """
    Собирает итоговый документ по ContextSpec:
      - для kind="section": возвращает рендер секции;
      - для kind="context": раскрывает шаблон и вложенные ${tpl:...}, подставляет секции.
    """

    def _parse_tpl_locator(ph: str, current_cfg_root: Path) -> Tuple[Path, str]:
        """
        Разбор локатора шаблона:
          - 'tpl:foo/bar'              -> (current_cfg_root, 'foo/bar')
          - 'tpl@apps/web:docs/guide'  -> (repo_root/apps/web/lg-cfg, 'docs/guide')
          - 'tpl@[apps/web]:foo'       -> (repo_root/apps/web/lg-cfg, 'foo')
        Возвращает (cfg_root, resource_name).
        """
        assert ph.startswith("tpl")
        # Варианты: 'tpl:NAME' | 'tpl@ORIGIN:NAME' | 'tpl@[ORIGIN]:NAME'
        if ph.startswith("tpl:"):
            return current_cfg_root, ph[4:]
        if ph.startswith("tpl@["):
            # tpl@[ORIGIN]:NAME
            close = ph.find("]:")
            if close < 0:
                raise RuntimeError(f"Invalid tpl locator (missing ']:' ): {ph}")
            origin = ph[5:close]  # между @[ ... ]
            name = ph[close + 2 :]
            if not origin:
                raise RuntimeError(f"Empty origin in tpl locator: {ph}")
            cfg = (repo_root / origin / "lg-cfg").resolve()
            if not cfg.is_dir():
                raise RuntimeError(f"Child lg-cfg not found: {cfg}")
            return cfg, name
        if ph.startswith("tpl@"):
            # tpl@ORIGIN:NAME
            colon = ph.find(":")
            if colon < 0:
                raise RuntimeError(f"Invalid tpl locator (missing ':'): {ph}")
            origin = ph[4:colon]
            name = ph[colon + 1 :]
            if not origin:
                raise RuntimeError(f"Empty origin in tpl locator: {ph}")
            cfg = (repo_root / origin / "lg-cfg").resolve()
            if not cfg.is_dir():
                raise RuntimeError(f"Child lg-cfg not found: {cfg}")
            return cfg, name
        raise RuntimeError(f"Unsupported tpl locator: {ph}")

    def _load_template_from(cfg_root: Path, name: str) -> Tuple[Path, str]:
        """
        Читает шаблон <cfg_root>/<name>.tpl.md без обращения к глобальным путям.
        """
        p = (cfg_root / f"{name}.tpl.md").resolve()
        if not p.is_file():
            raise RuntimeError(f"Template not found: {p}")
        return p, p.read_text(encoding="utf-8", errors="ignore")

    def _load_context(name: str) -> str:
        # Контекст всегда берём из «базового» (self) cfg_root.
        # Имена контекстов остаются локальными для верхнего уровня.
        p = context_path(repo_root, name)
        return p.read_text(encoding="utf-8", errors="ignore")

    def _expand_template(name: str, current_cfg_root: Path, templates: Dict[str, str]) -> Tuple[str, str]:
        """
        Рекурсивно расширяет один ШАБЛОН (.tpl.md).
        Возвращает (final_text, sections_only_text).
        """
        _p, src = _load_template_from(current_cfg_root, name)
        # В хэше учитываем «имя с происхождением» для стабильной диагностики
        templates[f"{current_cfg_root.as_posix()}::{name}"] = _sha1(src)

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
                # Вложенный шаблон в том же cfg_root
                child = ph[4:]
                child_final, child_sections_only = _expand_template(child, current_cfg_root, templates)
                out_final_parts.append(child_final)
                out_sections_only_parts.append(child_sections_only)
            elif ph.startswith("tpl@"):
                # Вложенный шаблон из дочернего cfg_root
                child_cfg_root, child_name = _parse_tpl_locator(ph, current_cfg_root)
                child_final, child_sections_only = _expand_template(child_name, child_cfg_root, templates)
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

    # context: стартуем с .ctx.md и раскрываем ${tpl:...}
    templates_hashes: Dict[str, str] = {}
    ctx_src = _load_context(spec.name)
    # Хэш самого контекста (для стабильности/диагностики), как раньше делали для корневого шаблона
    templates_hashes[f"{base_cfg_root.as_posix()}::ctx:{spec.name}"] = _sha1(ctx_src)

    out_final_parts: list[str] = []
    out_sections_only_parts: list[str] = []
    pos = 0
    for m in _Template.pattern.finditer(ctx_src):
        start, end = m.span()
        if start > pos:
            # клей из контекста уходит только в финальный документ
            out_final_parts.append(ctx_src[pos:start])
        ph = m.group("braced") or m.group("name") or ""
        if ph.startswith("tpl:"):
            child = ph[4:]
            child_final, child_sections_only = _expand_template(child, base_cfg_root, templates_hashes)
            out_final_parts.append(child_final)
            out_sections_only_parts.append(child_sections_only)
        elif ph.startswith("tpl@"):
            child_cfg_root, child_name = _parse_tpl_locator(ph, base_cfg_root)
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
