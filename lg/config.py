from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_VERSION = 1
DEFAULT_CFG_FILE = "listing_config.json"

_DEFAULT_CFG: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "extensions": [".py"],
    "exclude": [
        ".idea/",
        "__pycache__/",
        "**/__pycache__/**"
    ],
    "skip_empty": False,
    "skip_trivial_inits": False,
    "trivial_init_max_noncomment": 1,
}

def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return _DEFAULT_CFG.copy()

    with path.open(encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    if data.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported config schema {data.get('schema_version')} "
            f"(tool expects {SCHEMA_VERSION})"
        )

    merged = _DEFAULT_CFG.copy()
    merged.update(data)
    return merged
