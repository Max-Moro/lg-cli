from __future__ import annotations

from pathlib import Path
from typing import Set, Type

__all__ = ["BaseAdapter"]


class BaseAdapter:
    """Базовый класс адаптера языка."""
    #: Имя языка (python, java, …); для Base – 'base'
    name: str = "base"
    #: Набор поддерживаемых расширений
    extensions: Set[str] = set()
    #: Dataclass-конфиг, который loader передаёт адаптеру
    config_cls: Type | None = None

    # --- конфигурирование адаптера (инкапсуляция состояния) ---------------
    @classmethod
    def bind(cls, raw_cfg: dict | None) -> "BaseAdapter":
        """
        Фабрика «связанного» адаптера: создаёт инстанс и применяет cfg.
        Внешний код не видит тип конфигурации — полная инкапсуляция.
        """
        inst = cls()
        if cls.config_cls is None:
            inst._cfg = None
        else:
            inst._cfg = cls.config_cls(**(raw_cfg or {}))
        return inst

    # --- переопределяемая логика -------------------------------------------
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
