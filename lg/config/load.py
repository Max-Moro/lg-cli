from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from ruamel.yaml import YAML

from .model import Config, SectionCfg, SCHEMA_VERSION

_yaml = YAML(typ="safe")
_CFG_DIR = "lg-cfg"
_SECTIONS_FILE = "sections.yaml"


def _cfg_root(root: Path) -> Path:
    return (root / _CFG_DIR).resolve()


def _read_yaml_map(path: Path) -> dict:
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _collect_sections_from_sections_yaml(base: Path) -> Tuple[int, Dict[str, SectionCfg]]:
    """
    Читает lg-cfg/sections.yaml:
      - требует ключ 'schema_version' == SCHEMA_VERSION
      - все остальные ключи трактуются как секции с КОРОТКИМИ id (без префикса пути)
    """
    p = (base / _SECTIONS_FILE)
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


def _iter_fragment_files(base: Path) -> List[Path]:
    """
    Возвращает список всех **/*.sec.yaml внутри lg-cfg/ (кроме корневого sections.yaml).
    """
    out: List[Path] = []
    for p in base.rglob("*.sec.yaml"):
        # Корневой sections.yaml не является фрагментом
        if p.name == _SECTIONS_FILE and p.parent == base:
            continue
        out.append(p)
    out.sort()
    return out


def _canonical_prefix_for_fragment(base: Path, frag: Path) -> str:
    """
    Для файла lg-cfg/sub/pack.sec.yaml → канонический префикс 'sub/pack'
    (относительно lg-cfg/, POSIX).
    """
    rel = frag.resolve().relative_to(base.resolve())
    rel_posix = rel.as_posix()
    # снимаем хвост '.sec.yaml'
    if not rel_posix.endswith(".sec.yaml"):
        raise RuntimeError(f"Invalid fragment filename (expected *.sec.yaml): {frag}")
    stem = rel_posix[: -len(".sec.yaml")]
    return stem


def _collect_sections_from_fragments(base: Path) -> Dict[str, SectionCfg]:
    """
    Собирает секции из всех **/*.sec.yaml.
    Канонический ID секции = '<prefix>/<section_local_name>',
    где <prefix> = путь к файлу без суффикса '.sec.yaml' относительно lg-cfg/.
    """
    acc: Dict[str, SectionCfg] = {}
    for frag in _iter_fragment_files(base):
        raw = _read_yaml_map(frag)
        # schema_version в фрагментах — опционален, при наличии проверим и проигнорируем
        sv = raw.get("schema_version", None)
        if sv is not None and int(sv) != SCHEMA_VERSION:
            raise RuntimeError(f"{frag}: schema_version={sv} mismatches core {SCHEMA_VERSION}")
        prefix = _canonical_prefix_for_fragment(base, frag)
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
    base = _cfg_root(root)
    if not base.is_dir():
        raise RuntimeError(f"Config directory not found: {base}")

    _sv, core_sections = _collect_sections_from_sections_yaml(base)
    frag_sections = _collect_sections_from_fragments(base)

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