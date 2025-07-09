# pkg-инициализатор: loader + публичные re-export-ы

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ruamel.yaml import YAML

from lg.filters.model import FilterNode
from .model import Config, SCHEMA_VERSION
from ..adapters.markdown import LangMarkdown
from ..adapters.python import LangPython

__all__ = [
    "Config", "SCHEMA_VERSION",
    "load_config", "list_sections",
    "DEFAULT_CONFIG_DIR", "DEFAULT_CONFIG_FILE", "DEFAULT_SECTION_NAME",
]

#: Directory under project root containing the YAML config and contexts/
DEFAULT_CONFIG_DIR = "lg-cfg"
#: Name of the main YAML config file inside lg-cfg/
DEFAULT_CONFIG_FILE = "config.yaml"
DEFAULT_SECTION_NAME = "all"
_yaml = YAML(typ="safe")


# --------------------------------------------------------------------------- #
# PUBLIC LOADER
# --------------------------------------------------------------------------- #
def list_sections(path: Path) -> List[str]:
    """
    Вернуть список имён секций в мультисекционном конфиге.
    """
    if not path.exists():
        raise RuntimeError(f"Config file {path} not found")
    with path.open(encoding="utf-8") as f:
        raw_all: Dict[str, Any] = _yaml.load(f) or {}
    schema = raw_all.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported config schema {schema} (tool expects {SCHEMA_VERSION})"
        )
    # все ключи, кроме schema_version
    return [name for name in raw_all.keys() if name != "schema_version"]


def load_config(path: Path, section: str) -> Config:
    """
    Загрузить `section` из мультисекционного YAML и вернуть строго типизированный `Config`.
    При отсутствии файла или секции — бросить понятный RuntimeError.
    """
    if not path.exists():
        raise RuntimeError(f"Config file {path} not found")

    with path.open(encoding="utf-8") as f:
        raw_all: Dict[str, Any] = _yaml.load(f) or {}

    schema = raw_all.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported config schema {schema} (tool expects {SCHEMA_VERSION})"
        )

    if section not in raw_all:
        available = list_sections(path)
        raise RuntimeError(
            f"Section '{section}' not found in config. "
            f"Available sections: {', '.join(available)}"
        )

    raw: Dict[str, Any] = raw_all.get(section) or {}

    # --- адаптер Python (при отсутствии – будут дефолты из LangPython) ---
    py_cfg = LangPython(**raw.get("python", {}))

    # --- адаптер Markdown (при отсутствии – def max_heading_level=None) ---
    md_cfg = LangMarkdown(**raw.get("markdown", {}))

    # --- глобальная опция code_fence для всех файлов ---
    code_fence = bool(raw.get("code_fence", False))

    # --- дерево фильтров ---
    cfg_filters = FilterNode.from_dict(raw.get("filters", {"mode": "block"}))

    return Config(
        extensions=raw.get("extensions", [".py"]),
        filters=cfg_filters,
        skip_empty=raw.get("skip_empty", True),
        code_fence=code_fence,
        python=py_cfg,
        markdown=md_cfg,
    )
