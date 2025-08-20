from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from lg.io.model import FilterNode
from .model import Config, SectionCfg, SCHEMA_VERSION

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

        # Собираем фильтры
        filters = FilterNode.from_dict(node.get("filters", {"mode": "block"}))

        # Извлекаем «служебные» ключи секции и считаем остальные — конфигами адаптеров.
        service_keys = {"extensions", "filters", "skip_empty", "code_fence"}
        adapters_cfg: Dict[str, dict] = {}
        for k, v in node.items():
            if k in service_keys or k == "schema_version":
                continue
            if not isinstance(v, dict):
                raise RuntimeError(f"Adapter config for '{k}' in section '{name}' must be a mapping")
            adapters_cfg[str(k)] = dict(v)

        sections[name] = SectionCfg(
            extensions=exts,
            filters=filters,
            code_fence=bool(node.get("code_fence", True)),
            skip_empty=bool(node.get("skip_empty", True)),
            adapters=adapters_cfg,
        )

    return Config(schema_version=SCHEMA_VERSION, sections=sections)

def list_sections(root: Path) -> List[str]:
    cfg = load_config(root)
    return sorted(cfg.sections.keys())
