from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from ruamel.yaml import YAML

from .model import Config, SectionCfg, SCHEMA_VERSION
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


def _collect_sections_from_sections_yaml(root: Path) -> Tuple[int, Dict[str, SectionCfg]]:
    """
    Читает lg-cfg/sections.yaml:
      - требует ключ 'schema_version' == SCHEMA_VERSION
      - все остальные ключи трактуются как секции с КОРОТКИМИ id (без префикса пути)
    """
    p = sections_path(root)
    if not p.is_file():
        raise RuntimeError(f"Config file not found: {p}")
    raw = _read_yaml_map(p)
    sv = int(raw.get("schema_version", 0))
    if sv != SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported config schema {sv} (expected {SCHEMA_VERSION}) in {p}")
    sections: Dict[str, SectionCfg] = {}
    for name, node in raw.items():
        if name == "schema_version":
            continue
        if not isinstance(node, dict):
            raise RuntimeError(f"Section '{name}' in {p} must be a mapping")
        sections[name] = SectionCfg.from_dict(name, node)
    return sv, sections

def _collect_sections_from_fragments(root: Path) -> Dict[str, SectionCfg]:
    """
    Собирает секции из всех **/*.sec.yaml.
    Канонический ID секции = '<prefix>/<section_local_name>',
    где <prefix> = путь к файлу без суффикса '.sec.yaml' относительно lg-cfg/.
    """
    acc: Dict[str, SectionCfg] = {}
    for frag in iter_section_fragments(root):
        raw = _read_yaml_map(frag)
        # schema_version в фрагментах — опционален, при наличии проверим и проигнорируем
        sv = raw.get("schema_version", None)
        if sv is not None and int(sv) != SCHEMA_VERSION:
            raise RuntimeError(f"{frag}: schema_version={sv} mismatches core {SCHEMA_VERSION}")
        prefix = canonical_fragment_prefix(root, frag)
        for local_name, node in raw.items():
            if local_name == "schema_version":
                continue
            if not isinstance(node, dict):
                raise RuntimeError(f"Section '{local_name}' in {frag} must be a mapping")
            canon_id = f"{prefix}/{local_name}"
            acc[canon_id] = SectionCfg.from_dict(canon_id, node)
    return acc


def load_config(root: Path) -> Config:
    """
    Новая схема:
      • lg-cfg/sections.yaml — обязательный файл с schema_version и базовыми секциями
      • lg-cfg/**\/*.sec.yaml — произвольное число фрагментов секций
    """
    base = cfg_root(root)
    if not base.is_dir():
        raise RuntimeError(f"Config directory not found: {base}")

    _sv, core_sections = _collect_sections_from_sections_yaml(root)
    frag_sections = _collect_sections_from_fragments(root)

    # Сшиваем с проверкой дубликатов канонических ID
    all_sections: Dict[str, SectionCfg] = dict(core_sections)
    for k, v in frag_sections.items():
        if k in all_sections:
            raise RuntimeError(f"Duplicate section id: '{k}'")
        all_sections[k] = v

    return Config(schema_version=SCHEMA_VERSION, sections=all_sections)


def list_sections(root: Path) -> List[str]:
    cfg = load_config(root)
    return sorted(cfg.sections.keys())