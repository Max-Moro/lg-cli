from __future__ import annotations

from pathlib import Path

# Single source of truth for configuration directory structure.
CFG_DIR = "lg-cfg"
SECTIONS_FILE = "sections.yaml"
MODELS_FILE = "models.yaml"
MODES_FILE = "modes.yaml"
TAGS_FILE = "tags.yaml"


def cfg_root(root: Path) -> Path:
    """Absolute path to the lg-cfg/ directory."""
    return (root / CFG_DIR).resolve()


def models_path(root: Path) -> Path:
    """Path to the models configuration file lg-cfg/models.yaml."""
    return cfg_root(root) / MODELS_FILE


def modes_path(root: Path) -> Path:
    """Path to the modes configuration file lg-cfg/modes.yaml."""
    return cfg_root(root) / MODES_FILE


def tags_path(root: Path) -> Path:
    """Path to the tags configuration file lg-cfg/tags.yaml."""
    return cfg_root(root) / TAGS_FILE


def is_cfg_relpath(s: str) -> bool:
    """
    Quick check whether a relative POSIX path belongs to the lg-cfg/ directory.
    Used in tree traversal pruners.
    """
    return s == CFG_DIR or s.startswith(CFG_DIR + "/")
