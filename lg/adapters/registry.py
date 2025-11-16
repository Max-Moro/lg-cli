from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Type, Tuple

from .base import BaseAdapter

__all__ = [
    "register_lazy",
    "get_adapter_for_path",
    "list_implemented_adapters",
]


@dataclass(frozen=True)
class _LazySpec:
    module: str
    class_name: str
    extensions: Tuple[str, ...]


# Lazy specifications: ext → where the class is located
_LAZY_BY_EXT: Dict[str, _LazySpec] = {}

# Registered classes: by extension
_CLASS_BY_EXT: Dict[str, Type[BaseAdapter]] = {}


def register_lazy(*, module: str, class_name: str, extensions: List[str] | Tuple[str, ...]) -> None:
    """
    Register adapter "by strings" without importing the module.
    The same class can be declared for multiple extensions.
    """
    spec = _LazySpec(module=module, class_name=class_name, extensions=tuple(e.lower() for e in extensions))
    for ext in spec.extensions:
        _LAZY_BY_EXT[ext] = spec


def _load_adapter_from_spec(spec: _LazySpec) -> Type[BaseAdapter]:
    # Support both relative (".python") and absolute module names.
    mod = importlib.import_module(spec.module, package=__package__)
    cls = getattr(mod, spec.class_name, None)
    if cls is None:
        raise RuntimeError(f"Adapter class '{spec.class_name}' not found in {spec.module}")
    if not issubclass(cls, BaseAdapter):
        raise TypeError(f"{spec.module}.{spec.class_name} is not a subclass of BaseAdapter")

    # Register actual class (updates maps for all extensions of the class)
    for ext in cls.extensions:
        _CLASS_BY_EXT[ext.lower()] = cls

    return cls


def _resolve_class_by_ext(ext: str) -> Type[BaseAdapter]:
    # Is class already registered?
    cls = _CLASS_BY_EXT.get(ext)
    if cls:
        return cls
    # Is there a lazy spec?
    spec = _LAZY_BY_EXT.get(ext)
    if spec:
        return _load_adapter_from_spec(spec)
    # Fallback - base adapter
    return BaseAdapter


def get_adapter_for_path(path: Path) -> Type[BaseAdapter]:
    """
    Return adapter CLASS by path extension. Don't instantiate anything.
    If unknown - return BaseAdapter.
    """
    return _resolve_class_by_ext(path.suffix.lower())


def list_implemented_adapters() -> List[str]:
    """
    Return list of fully implemented language adapter names.

    Returns:
        List of adapter names (e.g.: ["python", "typescript", "markdown"])
    """
    implemented = set()

    # Iterate through all registered extensions
    for ext in _LAZY_BY_EXT.keys():
        try:
            adapter_cls = _resolve_class_by_ext(ext)
            # Skip base adapter
            if adapter_cls is not BaseAdapter:
                implemented.add(adapter_cls.name)
        except Exception:
            # Skip if failed to load
            continue

    return sorted(implemented)
