from __future__ import annotations

from pathlib import Path
from typing import Set, Type

__all__ = ["BaseAdapter", "get_adapter_for_path"]

_ADAPTERS_BY_EXT: dict[str, "BaseAdapter"] = {}
_ADAPTERS_BY_NAME: dict[str, "BaseAdapter"] = {}


class BaseAdapter:
    """Базовый класс адаптера языка."""
    #: Имя языка (python, java, …); для Base – 'base'
    name: str = "base"
    #: Набор поддерживаемых расширений
    extensions: Set[str] = set()
    #: Dataclass-конфиг, который loader передаёт адаптеру
    config_cls: Type | None = None

    # --- внутреннее состояние (сконфигурированный адаптер) -----------------
    def __init__(self):
        self._cfg = None  # тип зависит от конкретного адаптера

    # --- конфигурирование адаптера (инкапсуляция состояния) ---------------
    def bind(self, raw_cfg: dict | None) -> "BaseAdapter":
        """
        Возвращает новый экземпляр адаптера с установленной конфигурацией.
        Внешний код не видит тип конфигурации — полная инкапсуляция.
        """
        inst = self.__class__()  # новый экземпляр того же класса
        if self.config_cls is None:
            inst._cfg = None
        else:
            inst._cfg = self.config_cls(**(raw_cfg or {}))
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

    # --- регистрация --------------------------------------------------------
    @classmethod
    def register(cls, adapter_cls: Type["BaseAdapter"]):
        """
        Использовать как декоратор:

            @BaseAdapter.register
            class PythonAdapter(BaseAdapter): ...
        """
        inst = adapter_cls()                              # ← экземпляр *целевого* класса
        _ADAPTERS_BY_NAME[adapter_cls.name] = inst
        for ext in adapter_cls.extensions:
            _ADAPTERS_BY_EXT[ext] = inst
        return adapter_cls

# -------------------------------------------------------------------- #
#  Регистрируем «базовый» адаптер сразу при импорте модуля.
#  Он обслуживает файлы, для которых не найдено специфического адаптера.
# -------------------------------------------------------------------- #
_ADAPTERS_BY_NAME["base"] = BaseAdapter()

def get_adapter_for_path(path: Path) -> BaseAdapter:
    """Вернуть адаптер по расширению; если нет — базовый."""
    return _ADAPTERS_BY_EXT.get(path.suffix.lower(), _ADAPTERS_BY_NAME["base"])
