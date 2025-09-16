from __future__ import annotations

from pathlib import Path
from typing import List

# Единый источник правды для структуры каталога конфигурации.
CFG_DIR = "lg-cfg"
SECTIONS_FILE = "sections.yaml"
MODELS_FILE = "models.yaml"
MODES_FILE = "modes.yaml"
TAGS_FILE = "tags.yaml"


def cfg_root(root: Path) -> Path:
    """Абсолютный путь к каталогу lg-cfg/."""
    return (root / CFG_DIR).resolve()


def sections_path(root: Path) -> Path:
    """Путь к основному файлу секций lg-cfg/sections.yaml."""
    return cfg_root(root) / SECTIONS_FILE


def models_path(root: Path) -> Path:
    """Путь к файлу конфигурации моделей lg-cfg/models.yaml."""
    return cfg_root(root) / MODELS_FILE


def modes_path(root: Path) -> Path:
    """Путь к файлу конфигурации режимов lg-cfg/modes.yaml."""
    return cfg_root(root) / MODES_FILE


def tags_path(root: Path) -> Path:
    """Путь к файлу конфигурации тегов lg-cfg/tags.yaml."""
    return cfg_root(root) / TAGS_FILE


def iter_section_fragments(root: Path) -> List[Path]:
    """
    Все файлы с фрагментами секций: lg-cfg/**.sec.yaml (кроме корневого sections.yaml).
    Возвращает отсортированный список абсолютных путей.
    """
    base = cfg_root(root)
    out: List[Path] = []
    for p in base.rglob("*.sec.yaml"):
        # Случайный namesake не должен совпасть с корневым sections.yaml
        if p.name == SECTIONS_FILE and p.parent == base:
            continue
        out.append(p)
    out.sort()
    return out


def canonical_fragment_prefix(root: Path, frag: Path) -> str:
    """
    Для файла lg-cfg/sub/pack.sec.yaml → канонический префикс 'sub/pack'
    (относительно lg-cfg/, POSIX).
    """
    base = cfg_root(root)
    rel = frag.resolve().relative_to(base.resolve()).as_posix()
    if not rel.endswith(".sec.yaml"):
        raise RuntimeError(f"Invalid fragment filename (expected *.sec.yaml): {frag}")
    return rel[: -len(".sec.yaml")]


def is_cfg_relpath(s: str) -> bool:
    """
    Быстрая проверка, относится ли относительный POSIX-путь к каталогу lg-cfg/.
    Используется в pruner’ах обхода дерева.
    """
    return s == CFG_DIR or s.startswith(CFG_DIR + "/")
