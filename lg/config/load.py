from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from .model import Config, SectionCfg, SCHEMA_VERSION
from lg.io.model import FilterNode

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

        # --- адаптер Python (при отсутствии – будут дефолты из LangPython) ---
        from ..adapters.python import PythonCfg
        py_cfg = PythonCfg(**node.get("python", {}))

        # --- адаптер Markdown (при отсутствии – def max_heading_level=None) ---
        from ..adapters.markdown import MarkdownCfg
        md_cfg = MarkdownCfg(**node.get("markdown", {}))

        filters = FilterNode.from_dict(node.get("filters", {"mode": "block"}))
        sections[name] = SectionCfg(
            extensions=exts,
            filters=filters,
            code_fence=bool(node.get("code_fence", True)),
            skip_empty=bool(node.get("skip_empty", True)),
            markdown=md_cfg,
            python=py_cfg,
        )

    return Config(schema_version=SCHEMA_VERSION, sections=sections)

def list_sections(root: Path) -> List[str]:
    cfg = load_config(root)
    return sorted(cfg.sections.keys())
