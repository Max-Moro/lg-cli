from __future__ import annotations

from pathlib import Path
from typing import List

# Single source of truth for configuration directory structure.
CFG_DIR = "lg-cfg"
SECTIONS_FILE = "sections.yaml"
MODELS_FILE = "models.yaml"
MODES_FILE = "modes.yaml"
TAGS_FILE = "tags.yaml"


def cfg_root(root: Path) -> Path:
    """Absolute path to the lg-cfg/ directory."""
    return (root / CFG_DIR).resolve()


def sections_path(root: Path) -> Path:
    """Path to the main sections file lg-cfg/sections.yaml."""
    return cfg_root(root) / SECTIONS_FILE


def models_path(root: Path) -> Path:
    """Path to the models configuration file lg-cfg/models.yaml."""
    return cfg_root(root) / MODELS_FILE


def modes_path(root: Path) -> Path:
    """Path to the modes configuration file lg-cfg/modes.yaml."""
    return cfg_root(root) / MODES_FILE


def tags_path(root: Path) -> Path:
    """Path to the tags configuration file lg-cfg/tags.yaml."""
    return cfg_root(root) / TAGS_FILE


def iter_section_fragments(root: Path) -> List[Path]:
    """
    All section fragment files: lg-cfg/**.sec.yaml (excluding the root sections.yaml).
    Returns a sorted list of absolute paths.
    """
    base = cfg_root(root)
    out: List[Path] = []
    for p in base.rglob("*.sec.yaml"):
        # Random namesake should not match the root sections.yaml
        if p.name == SECTIONS_FILE and p.parent == base:
            continue
        out.append(p)
    out.sort()
    return out


def canonical_fragment_prefix(root: Path, frag: Path) -> str:
    """
    For file lg-cfg/sub/pack.sec.yaml → canonical prefix 'sub/pack'
    (relative to lg-cfg/, POSIX).
    """
    base = cfg_root(root)
    rel = frag.resolve().relative_to(base.resolve()).as_posix()
    if not rel.endswith(".sec.yaml"):
        raise RuntimeError(f"Invalid fragment filename (expected *.sec.yaml): {frag}")
    return rel[: -len(".sec.yaml")]


def is_cfg_relpath(s: str) -> bool:
    """
    Quick check whether a relative POSIX path belongs to the lg-cfg/ directory.
    Used in tree traversal pruners.
    """
    return s == CFG_DIR or s.startswith(CFG_DIR + "/")
