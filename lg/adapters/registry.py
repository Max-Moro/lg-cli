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


# Ленивые спецификации: ext → где лежит класс
_LAZY_BY_EXT: Dict[str, _LazySpec] = {}

# Разрешённые классы: по расширению
_CLASS_BY_EXT: Dict[str, Type[BaseAdapter]] = {}


def register_lazy(*, module: str, class_name: str, extensions: List[str] | Tuple[str, ...]) -> None:
    """
    Зарегистрировать адаптер «по строкам» без импорта модуля.
    Один и тот же класс можно объявлять по нескольким расширениям.
    """
    spec = _LazySpec(module=module, class_name=class_name, extensions=tuple(e.lower() for e in extensions))
    for ext in spec.extensions:
        _LAZY_BY_EXT[ext] = spec


def _load_adapter_from_spec(spec: _LazySpec) -> Type[BaseAdapter]:
    # Поддерживаем как относительные (".python") так и абсолютные имена модулей.
    mod = importlib.import_module(spec.module, package=__package__)
    cls = getattr(mod, spec.class_name, None)
    if cls is None:
        raise RuntimeError(f"Adapter class '{spec.class_name}' not found in {spec.module}")
    if not issubclass(cls, BaseAdapter):
        raise TypeError(f"{spec.module}.{spec.class_name} is not a subclass of BaseAdapter")

    # Регистрация реального класса (актуализирует карты по всем расширениям класса)
    for ext in cls.extensions:
        _CLASS_BY_EXT[ext.lower()] = cls

    return cls


def _resolve_class_by_ext(ext: str) -> Type[BaseAdapter]:
    # Уже зарегистрирован класс?
    cls = _CLASS_BY_EXT.get(ext)
    if cls:
        return cls
    # Есть ленивый spec?
    spec = _LAZY_BY_EXT.get(ext)
    if spec:
        return _load_adapter_from_spec(spec)
    # Фолбэк — базовый адаптер
    return BaseAdapter


def get_adapter_for_path(path: Path) -> Type[BaseAdapter]:
    """
    Вернуть КЛАСС адаптера по расширению пути. Ничего не инстанцируем.
    Если неизвестно — возвращаем BaseAdapter.
    """
    return _resolve_class_by_ext(path.suffix.lower())


def list_implemented_adapters() -> List[str]:
    """
    Возвращает список имен полностью реализованных языковых адаптеров.
    
    Returns:
        Список имен адаптеров (например: ["python", "typescript", "markdown"])
    """
    implemented = set()
    
    # Проходим по всем зарегистрированным расширениям
    for ext in _LAZY_BY_EXT.keys():
        try:
            adapter_cls = _resolve_class_by_ext(ext)
            # Пропускаем базовый адаптер
            if adapter_cls is not BaseAdapter:
                implemented.add(adapter_cls.name)
        except Exception:
            # Если не удалось загрузить - пропускаем
            continue
    
    return sorted(implemented)
