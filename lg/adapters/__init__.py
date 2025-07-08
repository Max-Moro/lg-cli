from __future__ import annotations
from importlib import import_module
from pkgutil import iter_modules

from .base import get_adapter_for_path  # noqa: F401

__all__ = ["get_adapter_for_path"]

# Импортируем все файлы-адаптеры, кроме base.py
for _, mod_name, _ in iter_modules(__path__):
    if mod_name not in {"base", "__init__"}:
        import_module(f"{__name__}.{mod_name}")
