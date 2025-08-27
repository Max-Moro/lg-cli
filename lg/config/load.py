from __future__ import annotations

from pathlib import Path
from typing import List

from ruamel.yaml import YAML

from .model import Config

_yaml = YAML(typ="safe")
_CFG_DIR = "lg-cfg"
_CFG_FILE = "config.yaml"

def _cfg_path(root: Path) -> Path:
    return (root / _CFG_DIR / _CFG_FILE).resolve()

def load_config(root: Path) -> Config:
    path = _cfg_path(root)
    if not path.is_file():
        raise RuntimeError(f"Config file not found: {path}")
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    from .model import Config
    return Config.from_dict(raw)

def list_sections(root: Path) -> List[str]:
    cfg = load_config(root)
    return sorted(cfg.sections.keys())
