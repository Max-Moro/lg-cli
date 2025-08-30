from __future__ import annotations

from importlib import metadata


def tool_version() -> str:
    """
    Единый способ получить версию установленного пакета.
    Не зависит от остальных модулей (во избежание циклов).
    """
    for dist in ("listing-generator", "lg"):
        try:
            return metadata.version(dist)
        except Exception:
            continue
    return "0.0.0"

__all__ = ["tool_version"]
