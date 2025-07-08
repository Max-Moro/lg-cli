# pkg-инициализатор: loader + публичные re-export-ы

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ruamel.yaml import YAML

from .model import Config, LangPython, SCHEMA_VERSION
from lg.filters.model import FilterNode

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

    filters_raw = raw.get("filters", {"mode": "block"})

    def _build_node(obj: Dict[str, Any], path: str = "") -> FilterNode:
        if "mode" not in obj:
            raise RuntimeError(f"Missing 'mode' in filters at '{path or '/'}'")

        node = FilterNode(
            mode=obj["mode"],
            allow=obj.get("allow", []),
            block=obj.get("block", []),
        )
        if node.empty_allow_warning():
            import logging

            logging.warning(
                "Filter at '%s' has mode=allow but empty allow-list → everything denied",
                path or "/",
            )

        for child_name, child_obj in obj.get("children", {}).items():
            node.children[child_name] = _build_node(child_obj, f"{path}/{child_name}")

        return node

    return Config(
        extensions=raw.get("extensions", [".py"]),
        filters=_build_node(filters_raw),
        skip_empty=raw.get("skip_empty", True),
        python=py_cfg,
    )
