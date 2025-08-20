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

    # --- ленивое построение конфигурации адаптера --------------------------
    def make_config(self, raw: dict | None):
        """
        Сконструировать dataclass-конфиг адаптера из сырого dict.
        Вызывается только при фактическом использовании адаптера.
        """
        if self.config_cls is None:
            return None
        return self.config_cls(**(raw or {}))

    # --- переопределяемая логика -------------------------------------------
    def should_skip(self, path: Path, text: str, cfg) -> bool:           # cfg → dataclass
        """True → файл исключается (языковые эвристики)."""
        return False

    # --- единый API с метаданными ---
    def process(self, text: str, cfg, group_size: int, mixed: bool) -> tuple[str, dict]:
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
