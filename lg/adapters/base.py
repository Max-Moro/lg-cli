from __future__ import annotations

from typing import Any, Generic, Optional, Set, Type, TypeVar, get_args

from .context import LightweightContext
from ..stats import TokenService

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
    # Cервис подсчёта токенов
    tokenizer: TokenService

    # --- Generic-интроспекция параметра C -----
    @classmethod
    def _resolve_cfg_type(cls) -> Type[C] | None:
        """
        Пытается извлечь конкретный тип C из объявления наследника BaseAdapter[C].
        Возвращает None, если адаптер не параметризован конфигом.
        """
        # Проходим по MRO и ищем первый конкретный тип конфигурации
        for kls in cls.__mro__:
            for base in getattr(kls, "__orig_bases__", ()) or ():
                args = get_args(base) or ()
                if args and not isinstance(args[0], TypeVar):
                    # Нашли конкретный тип (не TypeVar), возвращаем его
                    return args[0]
        return None

    # --- Конфигурирование адаптера -------------
    @classmethod
    def bind(cls: Type[A], raw_cfg: dict | None, tokenizer: TokenService) -> A:
        """
        Фабрика «связанного» адаптера: создаёт инстанс и применяет cfg.
        Внешний код не видит тип конфигурации — полная инкапсуляция.
        """
        inst = cls()
        inst._cfg = cls._load_cfg(raw_cfg)
        inst.tokenizer = tokenizer
        return inst

    @classmethod
    def _load_cfg(cls, raw_cfg: dict | None) -> C:
        """
        Универсальный загрузчик конфигурации для адаптера.
        Поведение по умолчанию:
          • Если у типа конфигурации есть статический метод `from_dict(dict)`,
            используем его (поддержка вложенных структур).
          • Иначе пытаемся вызвать конструктор как **kwargs.
        Адаптеры должны использовать дженерик подход, а не переопределять данный метод.
        """
        cfg_type = cls._resolve_cfg_type()
        if cfg_type is None:
            # У адаптера нет параметризованной конфигурации.
            return None

        # Удаляем служебный ключ секции 'empty_policy' (не относится к языковым адаптерам)
        cfg_input: dict[str, Any] = dict(raw_cfg or {})
        cfg_input.pop("empty_policy", None)

        # Есть статический конструктор from_dict?
        from_dict = getattr(cfg_type, "from_dict", None)
        if callable(from_dict):
            return from_dict(cfg_input)

        # Падаем обратно на прямую инициализацию через **kwargs.
        try:
            return cfg_type(**cfg_input)
        except TypeError as e:
            # Подсказываем разработчику адаптера/конфига, что стоит реализовать from_dict()
            raise TypeError(
                f"{cls.__name__}: cannot construct {cfg_type.__name__} from raw config keys "
                f"{sorted(cfg_input.keys())}; consider implementing {cfg_type.__name__}.from_dict(). "
                f"Original error: {e}"
            ) from e

    # Типобезопасный доступ к конфигу для наследников, у которых config_cls задан.
    # Для таких адаптеров self.cfg всегда C (а не Optional[C]).
    @property
    def cfg(self) -> C:
        if getattr(self, "_cfg", None) is None:
            # Для «безконфигового» адаптера или если bind() не вызывался.
            raise AttributeError(f"{self.__class__.__name__} has no bound config")
        return self._cfg

    # --- переопределяемая логика ------------------
    def should_skip(self, lightweight_ctx: 'LightweightContext') -> bool:
        """
        True → файл исключается (языковые эвристики).
        
        Args:
            lightweight_ctx: Облегченный контекст с информацией о файле
            
        Returns:
            True если файл должен быть пропущен
        """
        return False

    # --- единый API с метаданными ---
    def process(self, lightweight_ctx: 'LightweightContext') -> tuple[str, dict]:
        """
        Обрабатывает файл и возвращает (content, meta).
        
        Args:
            lightweight_ctx: Облегченный контекст с информацией о файле
            
        Returns:
            Tuple из обработанного содержимого и метаданных
        """
        return lightweight_ctx.raw_text, {}
