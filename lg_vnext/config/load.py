from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from .model import ConfigV6, SectionCfg, MarkdownCfg, PythonCfg, SCHEMA_VERSION

_yaml = YAML(typ="safe")
_CFG_DIR = "lg-cfg"
_CFG_FILE = "config.yaml"

def _cfg_path(root: Path) -> Path:
    return (root / _CFG_DIR / _CFG_FILE).resolve()

def load_config_v6(root: Path) -> ConfigV6:
    path = _cfg_path(root)
    if not path.is_file():
        raise RuntimeError(f"Config file not found: {path}")
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    sv = raw.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported config schema {sv} (expected {SCHEMA_VERSION})")

    # Собираем секции: все ключи, кроме schema_version, считаем секциями
    sections: Dict[str, SectionCfg] = {}
    for name, node in raw.items():
        if name == "schema_version":
            continue
        if not isinstance(node, dict):
            raise RuntimeError(f"Section '{name}' must be a mapping")
        # Разбираем минимальные поля для этого шага
        exts = list(map(str, node.get("extensions", [".py"])))
        md = node.get("markdown", {}) or {}
        py = node.get("python", {}) or {}
        code_fence = bool(node.get("code_fence", True))
        sections[name] = SectionCfg(
            extensions=exts,
            markdown=MarkdownCfg(max_heading_level=md.get("max_heading_level")),
            python=PythonCfg(
                skip_empty=bool(py.get("skip_empty", True)),
                skip_trivial_inits=bool(py.get("skip_trivial_inits", True)),
                trivial_init_max_noncomment=int(py.get("trivial_init_max_noncomment", 1)),
            ),
            code_fence=code_fence,
        )

    return ConfigV6(schema_version=SCHEMA_VERSION, sections=sections)

def list_sections(root: Path) -> List[str]:
    cfg = load_config_v6(root)
    return sorted(cfg.sections.keys())
