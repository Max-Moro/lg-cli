from __future__ import annotations
from pathlib import Path
from typing import Dict, Set, Type

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

    # --- переопределяемая логика -------------------------------------------
    def should_skip(self, path: Path, text: str, cfg) -> bool:           # cfg → dataclass
        """True → файл исключается (языковые эвристики)."""
        return False

    def process(self, text: str, cfg, group_size: int, mixed: bool) -> str:
        """
        Точка расширения для адаптеров: обрабатывает тело файла перед вставкой.
        По умолчанию ничего не меняем.
        :param text: исходный текст
        :param cfg: соответствующий dataclass-конфиг (или None)
        :param group_size: сколько файлов в этой языковой группе
        :param mixed: смешивается ли листинг с другими типами языков
        """
        return text

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
