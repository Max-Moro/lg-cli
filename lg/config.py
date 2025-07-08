from __future__ import annotations
from ruamel.yaml import YAML
from pathlib import Path
from typing import Any, Dict

SCHEMA_VERSION = 2
DEFAULT_CFG_FILE = "listing_config.yaml"

# --------------------------------------------------------------------------- #
# ДЕФОЛТЫ ТОЛЬКО ДЛЯ ГЛОБАЛЬНОГО УРОВНЯ
# (языковые значения живут в адаптерах: python_.py, java_.py, …)
# --------------------------------------------------------------------------- #
_DEFAULT_CFG: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "extensions": [".py"],
    "exclude": [
        ".idea/",
        "__pycache__/",
        "**/__pycache__/**",
    ],
    # работает, если ЯЗЫК НЕ РАСПОЗНАН или нет секции языка
    "skip_empty": True,
}

# --------------------------------------------------------------------------- #
# YAML loader
# --------------------------------------------------------------------------- #
_yaml = YAML(typ="safe")

# --------------------------------------------------------------------------- #
# HELPERS
# --------------------------------------------------------------------------- #
def _merge_defaults(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Накладываем значения пользователя поверх глобальных дефолтов."""
    cfg = _DEFAULT_CFG.copy()
    cfg.update(raw)                      # пользовательские ключи перекрывают
    return cfg


# --------------------------------------------------------------------------- #
# PUBLIC API
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> Dict[str, Any]:
    """
    Загрузить listing_config.json.

    • Если файла нет — вернуть дефолты.
    • Если schema_version отсутствует — считаем, что это актуальная версия.
    • Проверяем несовместимость схем.
    • НЕ вмешиваемся в секции языков: они разбираются внутри адаптеров.
    """
    if not path.exists():
        return _DEFAULT_CFG.copy()

    with path.open(encoding="utf-8") as f:
        raw: Dict[str, Any] = _yaml.load(f) or {}

    if raw.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported config schema {raw.get('schema_version')} "
            f"(tool expects {SCHEMA_VERSION})"
        )

    return _merge_defaults(raw)
