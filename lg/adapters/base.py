from __future__ import annotations

from pathlib import Path
from typing import Generic, Optional, Set, Type, TypeVar, get_args, get_origin
from lg.conf import build_typed

__all__ = ["BaseAdapter"]

C = TypeVar("C")  # тип конфигурации конкретного адаптера
A = TypeVar("A", bound="BaseAdapter[Any]")


class BaseAdapter(Generic[C]):
    """Базовый класс адаптера языка."""
    #: Имя языка (python, java, …); для Base – 'base'
    name: str = "base"
    #: Набор поддерживаемых расширений
    extensions: Set[str] = set()
    #: Храним связанный конфиг (может быть None для «безконфиговых» адаптеров)
    _cfg: Optional[C]

    # --- Generic-интроспекция параметра C -----
    @classmethod
    def _resolve_cfg_type(cls) -> Type[C] | None:
        """
        Пытается извлечь конкретный тип C из объявления наследника BaseAdapter[C].
        Возвращает None, если адаптер не параметризован конфигом.
        """
        # Проходим по MRO и смотрим __orig_bases__ у каждого класса
        for kls in cls.__mro__:
            for base in getattr(kls, "__orig_bases__", ()) or ():
                if get_origin(base) is BaseAdapter:
                    args = get_args(base) or ()
                    if args:
                        return args[0]
        return None

    # --- Конфигурирование адаптера -------------
    @classmethod
    def bind(cls: Type[A], raw_cfg: dict | None) -> A:
        """
        Фабрика «связанного» адаптера: создаёт инстанс и применяет cfg.
        Внешний код не видит тип конфигурации — полная инкапсуляция.
        """
        inst = cls()
        cfg_type = cls._resolve_cfg_type()
        if cfg_type is None:
            inst._cfg = None
        else:
            # Строго приводим конфиг к типу (поддержка вложенных dataclass/pydantic)
            # Исключаем служебный ключ 'empty_policy' (секционная политика пустых файлов).
            cfg_map = dict(raw_cfg or {})
            cfg_map.pop("empty_policy", None)
            inst._cfg = build_typed(cfg_type, cfg_map)
        return inst

    # Типобезопасный доступ к конфигу для наследников, у которых config_cls задан.
    # Для таких адаптеров self.cfg всегда C (а не Optional[C]).
    @property
    def cfg(self) -> C:
        if getattr(self, "_cfg", None) is None:
            # Для «безконфигового» адаптера или если bind() не вызывался.
            raise AttributeError(f"{self.__class__.__name__} has no bound config")
        return self._cfg

    # --- переопределяемая логика ------------------
    def should_skip(self, path: Path, text: str) -> bool:
        """True → файл исключается (языковые эвристики)."""
        return False

    # --- единый API с метаданными ---
    def process(self, text: str, group_size: int, mixed: bool) -> tuple[str, dict]:
        """
        Возвращает (content, meta), где meta — произвольный словарь
        (например: {"removed_comments": 120, "kept_signatures": 34}).
        Базовая реализация — идентичность текста без метаданных.
        """
        return text, {}
