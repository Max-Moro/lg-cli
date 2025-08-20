from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Type, Tuple

from .base import BaseAdapter

__all__ = [
    "register_lazy",
    "register_class",
    "get_adapter_for_path",
]


@dataclass(frozen=True)
class _LazySpec:
    module: str
    class_name: str
    extensions: Tuple[str, ...]


# Ленивые спецификации: ext → где лежит класс
_LAZY_BY_EXT: Dict[str, _LazySpec] = {}

# Разрешённые классы: по имени и по расширению
_CLASS_BY_NAME: Dict[str, Type[BaseAdapter]] = {}
_CLASS_BY_EXT: Dict[str, Type[BaseAdapter]] = {}


def register_lazy(*, module: str, class_name: str, extensions: List[str] | Tuple[str, ...]) -> None:
    """
    Зарегистрировать адаптер «по строкам» без импорта модуля.
    Один и тот же класс можно объявлять по нескольким расширениям.
    """
    spec = _LazySpec(module=module, class_name=class_name, extensions=tuple(e.lower() for e in extensions))
    for ext in spec.extensions:
        _LAZY_BY_EXT[ext] = spec


def register_class(adapter_cls: Type[BaseAdapter]) -> None:
    """
    Регистрация *класса* адаптера (вызывается декоратором BaseAdapter.register
    в момент импорта реального модуля адаптера).
    """
    _CLASS_BY_NAME[adapter_cls.name] = adapter_cls
    for ext in adapter_cls.extensions:
        _CLASS_BY_EXT[ext.lower()] = adapter_cls


def _load_adapter_from_spec(spec: _LazySpec) -> Type[BaseAdapter]:
    # Поддерживаем как относительные (".python") так и абсолютные имена модулей.
    mod = importlib.import_module(spec.module, package=__package__)
    cls = getattr(mod, spec.class_name, None)
    if cls is None:
        raise RuntimeError(f"Adapter class '{spec.class_name}' not found in {spec.module}")
    if not issubclass(cls, BaseAdapter):
        raise TypeError(f"{spec.module}.{spec.class_name} is not a subclass of BaseAdapter")
    # Регистрация реального класса (актуализирует карты по всем расширениям класса)
    register_class(cls)
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
