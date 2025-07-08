# pkg-инициализатор: loader + публичные re-export-ы

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from ruamel.yaml import YAML

from .model import Config, LangPython, SCHEMA_VERSION

__all__ = ["Config", "LangPython", "SCHEMA_VERSION", "load_config", "DEFAULT_CFG_FILE"]

DEFAULT_CFG_FILE = "listing_config.yaml"
_yaml = YAML(typ="safe")


# --------------------------------------------------------------------------- #
# PUBLIC LOADER
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> Config:
    """
    Загрузить `listing_config.yaml` и вернуть строго типизированный `Config`.
    Если файл отсутствует — вернуть объект с дефолтами.
    """
    if not path.exists():
        return Config()

    with path.open(encoding="utf-8") as f:
        raw: Dict[str, Any] = _yaml.load(f) or {}

    if raw.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported config schema {raw.get('schema_version')} "
            f"(tool expects {SCHEMA_VERSION})"
        )

    py_cfg = LangPython(**raw.get("python", {}))

    return Config(
        extensions=raw.get("extensions", [".py"]),
        filters=raw.get("filters", {}),
        exclude=raw.get("exclude", []),
        skip_empty=raw.get("skip_empty", True),
        python=py_cfg,
    )