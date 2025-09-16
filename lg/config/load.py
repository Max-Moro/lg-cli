from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from lg.migrate import ensure_cfg_actual
from .model import Config, SectionCfg
from .paths import (
    cfg_root,
    sections_path,
    iter_section_fragments,
    canonical_fragment_prefix,
)

_yaml = YAML(typ="safe")


def _read_yaml_map(path: Path) -> dict:
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _collect_sections_from_sections_yaml(root: Path) -> Dict[str, SectionCfg]:
    """
    Читает lg-cfg/sections.yaml. Все ключи трактуются как секции с КОРОТКИМИ id (без префикса пути)
    """
    p = sections_path(root)
    if not p.is_file():
        return {}
    raw = _read_yaml_map(p)
    sections: Dict[str, SectionCfg] = {}
    for name, node in raw.items():
        if not isinstance(node, dict):
            raise RuntimeError(f"Section '{name}' in {p} must be a mapping")
        sections[name] = SectionCfg.from_dict(name, node)
    return sections

def _collect_sections_from_fragments(root: Path) -> Dict[str, SectionCfg]:
    """
    Собирает секции из всех **/*.sec.yaml.
    Канонический ID секции формируется так:
      • Если фрагмент содержит РОВНО одну секцию → канон-ID = <имя этой секции> (префикс игнорируем).
        Пример: 'web.sec.yaml' c единственной секцией 'web-api' → 'web-api'.
      • Иначе:
          – prefix = путь к файлу без суффикса '.sec.yaml' относительно lg-cfg/ (POSIX).
          – Если последний сегмент prefix совпадает с именем секции → канон-ID = prefix
            (устраняем "a/a", "pkg/core/core").
          – Иначе → канон-ID = 'prefix/<section_local_name>'.
    """
    acc: Dict[str, SectionCfg] = {}
    for frag in iter_section_fragments(root):
        raw = _read_yaml_map(frag)
        prefix = canonical_fragment_prefix(root, frag)

        # Соберём список секций
        section_items = [(name, node) for name, node in raw.items()]
        if not section_items:
            # Пустой фрагмент — корректен, но нечего добавлять
            continue

        pref_tail = prefix.split("/")[-1] if prefix else ""
        for local_name, node in section_items:
            if not isinstance(node, dict):
                raise RuntimeError(f"Section '{local_name}' in {frag} must be a mapping")
            # Нормализация канон-ID без повторения хвоста (исправляет "a/a" и т. п.)
            canon_id = prefix if (pref_tail and local_name == pref_tail) else f"{prefix}/{local_name}"
            acc[canon_id] = SectionCfg.from_dict(canon_id, node)
    return acc


def load_config(root: Path) -> Config:
    """
    Схема:
      • lg-cfg/sections.yaml — файл с базовыми секциями
      • lg-cfg/**\/*.sec.yaml — произвольное число фрагментов секций
    """
    base = cfg_root(root)
    if not base.is_dir():
        raise RuntimeError(f"Config directory not found: {base}")
    # Перед любым чтением приводим lg-cfg/ к актуальному формату
    ensure_cfg_actual(base)

    core_sections = _collect_sections_from_sections_yaml(root)
    frag_sections = _collect_sections_from_fragments(root)

    # Сшиваем с проверкой дубликатов канонических ID
    all_sections: Dict[str, SectionCfg] = dict(core_sections)
    for k, v in frag_sections.items():
        if k in all_sections:
            raise RuntimeError(f"Duplicate section id: '{k}'")
        all_sections[k] = v

    return Config(sections=all_sections)


def list_sections(root: Path) -> List[str]:
    """
    Строгий список (через load_config) — МИГРАЦИИ ВОЗМОЖНЫ.
    Используется там, где формат гарантированно актуален.
    """
    cfg = load_config(root)
    return sorted(cfg.sections.keys())

def list_sections_peek(root: Path) -> List[str]:
    """
    Безопасный список без запуска миграций.
    Читает lg-cfg/sections.yaml и все **/*.sec.yaml напрямую.
    """
    base = cfg_root(root)
    if not base.is_dir():
        return []
    core = _collect_sections_from_sections_yaml(root)
    frags = _collect_sections_from_fragments(root)
    return sorted({*core.keys(), *frags.keys()})
