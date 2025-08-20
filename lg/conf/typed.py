from __future__ import annotations

import dataclasses
import enum
import typing as t
from dataclasses import is_dataclass, fields

try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover
    BaseModel = t.cast(t.Type[object], object)  # sentinel fallback


class ConfigCoerceError(TypeError):
    """Ошибка приведения конфигурации к типу с указанием пути."""
    def __init__(self, message: str, path: tuple[str, ...] = ()):
        self.path = path
        prefix = f"{'.'.join(path)}: " if path else ""
        super().__init__(prefix + message)


_T = t.TypeVar("_T")


def build_typed(cls: type[_T], data: t.Any) -> _T:
    """
    Построить типизированный объект по классу (dataclass или pydantic BaseModel),
    рекурсивно приводя вложенные структуры согласно type hints.
    """
    try:
        return t.cast(_T, _coerce_to_class(cls, data, path=()))
    except ConfigCoerceError:
        raise
    except Exception as e:
        raise ConfigCoerceError(f"failed to build {getattr(cls, '__name__', str(cls))}: {e}") from e


def _coerce_to_class(cls: type, data: t.Any, path: tuple[str, ...]):
    # Pydantic v2: предпочитаем их собственную валидацию
    if isinstance(cls, type) and issubclass(cls, BaseModel):  # type: ignore[arg-type]
        if not isinstance(data, dict):
            raise ConfigCoerceError(f"expected mapping for {cls.__name__}, got {type(data).__name__}", path)
        try:
            return cls.model_validate(data)  # type: ignore[attr-defined]
        except Exception as e:
            raise ConfigCoerceError(str(e), path)

    # Dataclass
    if is_dataclass(cls):
        if not isinstance(data, dict):
            raise ConfigCoerceError(f"expected mapping for {cls.__name__}, got {type(data).__name__}", path)
        # строгая проверка лишних ключей
        allowed = {f.name for f in fields(cls)}
        extras = set(data.keys()) - allowed
        if extras:
            raise ConfigCoerceError(f"unexpected keys: {sorted(extras)!r}", path)

        kwargs = {}
        for f in fields(cls):
            f_path = (*path, f.name)
            if f.name in data:
                kwargs[f.name] = coerce(data[f.name], f.type, f_path)
            else:
                # использовать default/default_factory, иначе ошибка
                if f.default is not dataclasses.MISSING:
                    kwargs[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:  # type: ignore[attr-defined]
                    kwargs[f.name] = f.default_factory()  # type: ignore[misc]
                else:
                    raise ConfigCoerceError("required field missing", f_path)
        return cls(**kwargs)  # type: ignore[misc]

    # Прочие классы (в т.ч. BaseModel не попавший под ветку) — пробуем напрямую
    if isinstance(data, cls):
        return data
    try:
        return cls(data)  # last-resort cast
    except Exception:
        raise ConfigCoerceError(f"cannot coerce {type(data).__name__} → {getattr(cls, '__name__', str(cls))}", path)


def coerce(value: t.Any, hint: t.Any, path: tuple[str, ...]) -> t.Any:
    """Рекурсивная нормализация согласно типу-подсказке."""
    origin = t.get_origin(hint)
    args = t.get_args(hint)

    # Any — пропускаем
    if hint is t.Any or hint is None:  # None как тип (редко)
        return value

    # Optional[T] / Union[…]
    if origin is t.Union:
        # None допустим?
        if value is None and type(None) in args:
            return None
        last_err: Exception | None = None
        for option in args:
            if option is type(None):
                continue
            try:
                return coerce(value, option, path)
            except Exception as e:
                last_err = e
        # не подошёл ни один вариант
        raise last_err if last_err else ConfigCoerceError("union alternatives exhausted", path)

    # Литералы
    if origin is t.Literal:
        if value not in args:
            raise ConfigCoerceError(f"expected one of {args!r}, got {value!r}", path)
        return value

    # Примитивы
    if hint in (str, int, float, bool):
        if isinstance(value, hint):
            return value
        # YAML обычно даёт правильные типы, но попробуем мягкое приведение
        try:
            return hint(value)
        except Exception:
            raise ConfigCoerceError(f"expected {hint.__name__}, got {type(value).__name__}", path)

    # Enum
    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        if isinstance(value, hint):
            return value
        # по имени или по значению
        try:
            return hint[value]  # type: ignore[index]
        except Exception:
            try:
                return hint(value)  # type: ignore[call-arg]
            except Exception:
                raise ConfigCoerceError(f"expected {hint.__name__} (by name or value), got {value!r}", path)

    # Словари
    if origin is dict or origin is t.Dict:
        k_t, v_t = args or (t.Any, t.Any)
        if not isinstance(value, dict):
            raise ConfigCoerceError(f"expected dict, got {type(value).__name__}", path)
        out = {}
        for k, v in value.items():
            kk = coerce(k, k_t, (*path, "<key>"))
            vv = coerce(v, v_t, (*path, str(kk)))
            out[kk] = vv
        return out

    # Списки
    if origin is list or origin is t.List:
        (elem_t,) = args or (t.Any,)
        if not isinstance(value, list):
            raise ConfigCoerceError(f"expected list, got {type(value).__name__}", path)
        return [coerce(v, elem_t, (*path, str(i))) for i, v in enumerate(value)]

    # Множества
    if origin is set or origin is t.Set:
        (elem_t,) = args or (t.Any,)
        if not isinstance(value, (set, list, tuple)):
            raise ConfigCoerceError(f"expected set/list, got {type(value).__name__}", path)
        return {coerce(v, elem_t, (*path, str(i))) for i, v in enumerate(value)}

    # Кортежи
    if origin is tuple or origin is t.Tuple:
        if not isinstance(value, (list, tuple)):
            raise ConfigCoerceError(f"expected tuple/list, got {type(value).__name__}", path)
        # Tuple[T, ...] или Tuple[T1, T2, ...]
        if len(args) == 2 and args[1] is t.Any:  # Tuple[T, Any] — экзотика
            elem_t = args[0]
            return tuple(coerce(v, elem_t, (*path, str(i))) for i, v in enumerate(value))
        if len(args) == 2 and args[1] is Ellipsis:
            elem_t = args[0]
            return tuple(coerce(v, elem_t, (*path, str(i))) for i, v in enumerate(value))
        if args:
            if len(args) != len(value):
                raise ConfigCoerceError(f"expected tuple of len={len(args)}, got {len(value)}", path)
            return tuple(coerce(v, at, (*path, str(i))) for i, (v, at) in enumerate(zip(value, args)))
        return tuple(value)

    # Dataclass / Pydantic / Прочее
    if isinstance(hint, type):
        return _coerce_to_class(hint, value, path)

    # Падение по умолчанию
    return value
