from __future__ import annotations

from importlib import metadata


def tool_version() -> str:
    """
    Single way to get the version of the installed package.
    Independent from other modules (to avoid cycles).
    """
    for dist in ("listing-generator", "lg"):
        try:
            return metadata.version(dist)
        except Exception:
            continue
    return "0.0.0"

__all__ = ["tool_version"]
