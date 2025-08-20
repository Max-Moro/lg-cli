from __future__ import annotations

import dataclasses
import os
import sys
import typing as t
from dataclasses import fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, get_args, get_origin

import logging

# -------------------- Logging setup --------------------

_LOG = logging.getLogger("lg.config.typed")

def _setup_logging_once() -> None:
    if getattr(_setup_logging_once, "_inited", False):
        return
    _setup_logging_once._inited = True  # type: ignore[attr-defined]
    level = logging.DEBUG if os.environ.get("LG_TYPED_DEBUG") else logging.INFO
    _LOG.setLevel(level)
    if not _LOG.handlers:
        h = logging.StreamHandler()
        fmt = logging.Formatter("[%(levelname)s] %(message)s")
        h.setFormatter(fmt)
        _LOG.addHandler(h)

_setup_logging_once()

# -------------------- Pydantic detection --------------------

try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover
    BaseModel = t.cast(t.Type[object], object)

# -------------------- Public error --------------------

class ConfigLoadError(ValueError):
    """Ошибка типизированной загрузки конфигурации с указанием пути поля."""
    pass

# -------------------- Helpers --------------------

def _type_name(tp: Any) -> str:
    try:
        return tp.__name__  # type: ignore[attr-defined]
    except Exception:
        return str(tp)

def _err(path: str, msg: str) -> ConfigLoadError:
    _LOG.debug("RAISE at %s: %s", path, msg)
    return ConfigLoadError(f"{path}: {msg}")

def _is_base_model(tp: Any) -> bool:
    try:
        return isinstance(tp, type) and issubclass(tp, BaseModel)  # type: ignore[arg-type]
    except Exception:
        return False

def _strip_annotated(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is t.Annotated:
        args = get_args(tp)
        return args[0] if args else Any
    return tp

def _coerce_literal(val: Any, tp: Any, path: str) -> Any:
    allowed = set(get_args(tp))
    _LOG.debug("Literal at %s: allowed=%s, val=%r", path, allowed, val)
    if val in allowed:
        return val
    raise _err(path, f"expected Literal {allowed}, got {val!r}")

def _coerce_enum(val: Any, tp: Any, path: str) -> Any:
    _LOG.debug("Enum at %s: enum=%s, val=%r (%s)", path, _type_name(tp), val, type(val).__name__)
    if isinstance(val, tp):
        return val
    if isinstance(val, str):
        try:
            return tp[val]  # by name
        except Exception:
            pass
    try:
        return tp(val)  # by value
    except Exception:
        raise _err(path, f"expected enum {_type_name(tp)}, got {val!r}")

def _coerce_union(val: Any, tp: Any, path: str) -> Any:
    variants = get_args(tp)
    _LOG.debug("Union at %s: variants=%s, val=%r", path, [ _type_name(a) for a in variants ], val)
    errs: list[str] = []
    for sub in variants:
        # Спец-обработка Optional: NoneType матчится ТОЛЬКО при val is None.
        if sub is type(None):
            if val is None:
                _LOG.debug("Union branch None matched at %s", path)
                return None
            # val не None → эту ветку пропускаем
            _LOG.debug("Union branch NoneType skipped at %s (val is not None)", path)
            continue
        try:
            res = load_typed(sub, val, path=path)
            _LOG.debug("Union branch %s matched at %s → %r", _type_name(sub), path, res)
            return res
        except ConfigLoadError as e:
            errs.append(str(e))
            continue
    raise _err(path, " | ".join(errs) or f"no variant of {_type_name(tp)} matched")

def _coerce_mapping(val: Any, tp: Any, path: str) -> Any:
    origin = get_origin(tp)
    _LOG.debug("Mapping at %s: origin=%s, val-type=%s", path, origin, type(val).__name__)
    if not isinstance(val, dict):
        raise _err(path, f"expected dict, got {type(val).__name__}")
    args = get_args(tp) or (Any, Any)
    kt, vt = args[0], args[1]
    out: dict[Any, Any] = {}
    for k, v in val.items():
        k2 = load_typed(kt, k, path=f"{path}.<key>")
        v2 = load_typed(vt, v, path=f"{path}.{k2!r}")
        out[k2] = v2
    return out

def _coerce_sequence(val: Any, tp: Any, path: str) -> Any:
    origin = get_origin(tp)
    _LOG.debug("Sequence at %s: origin=%s, val-type=%s", path, origin, type(val).__name__)
    if not isinstance(val, (list, tuple, set)):
        raise _err(path, f"expected sequence {origin}, got {type(val).__name__}")
    (et,) = get_args(tp) or (Any,)
    items = [load_typed(et, v, path=f"{path}[{i}]") for i, v in enumerate(val)]
    if origin is list or origin is t.List:
        return items
    if origin is tuple or origin is t.Tuple:
        return tuple(items)
    if origin is set or origin is t.Set:
        return set(items)
    return items

def _build_globalns_for(tp: Any) -> dict[str, Any]:
    """
    Собираем глобальное пространство имён для get_type_hints:
      • базируемся на module.__dict__ класса;
      • дополнительно подкладываем цепочку пакетов ('lg', 'lg.markdown', ...),
        чтобы выражения типа 'lg.markdown.model.MarkdownDropCfg' в строковых
        аннотациях успешно вычислялись.
    """
    mod = sys.modules.get(tp.__module__)
    gns: dict[str, Any] = {}
    if mod and hasattr(mod, "__dict__"):
        gns.update(mod.__dict__)  # type: ignore[arg-type]
    # подложить пакеты
    pkg_path = tp.__module__.split(".")
    for i in range(1, len(pkg_path)+1):
        pkg_name = ".".join(pkg_path[:i])
        pkg = sys.modules.get(pkg_name)
        if pkg is not None:
            root = pkg_path[0]
            # в globals должны быть прямые имена (например, 'lg')
            gns.setdefault(pkg_name, pkg)
            gns.setdefault(root, sys.modules.get(root))
    return gns

def _resolve_type_hints_for_class(tp: Any) -> dict[str, Any]:
    gns = _build_globalns_for(tp)
    try:
        hints = t.get_type_hints(tp, globalns=gns, localns=None, include_extras=True)  # py3.11+
    except TypeError:
        hints = t.get_type_hints(tp, globalns=gns, localns=None)
    _LOG.debug("Type hints for %s: %s", _type_name(tp), {k: str(v) for k, v in hints.items()})
    return hints

def _coerce_dataclass(val: Any, tp: Any, path: str) -> Any:
    _LOG.debug("Dataclass at %s: %s, val-type=%s", path, _type_name(tp), type(val).__name__)
    if not isinstance(val, dict):
        raise _err(path, f"expected mapping for dataclass {_type_name(tp)}, got {type(val).__name__}")
    type_hints = _resolve_type_hints_for_class(tp)
    fld_map = {f.name: f for f in fields(tp)}
    extras = set(val.keys()) - set(fld_map.keys())
    if extras:
        raise _err(path, f"unknown key(s): {sorted(extras)}")
    kwargs: dict[str, Any] = {}
    for name, f in fld_map.items():
        sub_path = f"{path}.{name}"
        ftype = type_hints.get(name, f.type)
        _LOG.debug("  Field %s → type=%s; present=%s", sub_path, ftype, name in val)
        if name in val:
            kwargs[name] = load_typed(ftype, val[name], path=sub_path)
        else:
            if f.default is not dataclasses.MISSING or getattr(f, "default_factory", dataclasses.MISSING) is not dataclasses.MISSING:  # type: ignore[attr-defined]
                _LOG.debug("  Field %s: using dataclass default", sub_path)
                continue
            ftype0 = _strip_annotated(ftype)
            if get_origin(ftype0) in (t.Union, UnionType) and type(None) in get_args(ftype0):
                kwargs[name] = None
                _LOG.debug("  Field %s: Optional missing → None", sub_path)
            else:
                raise _err(sub_path, "required field missing")
    inst = tp(**kwargs)
    _LOG.debug("Dataclass built at %s: %r", path, inst)
    return inst

def _coerce_pydantic(val: Any, tp: Any, path: str) -> Any:
    _LOG.debug("Pydantic at %s: %s", path, _type_name(tp))
    try:
        return tp.model_validate(val)  # type: ignore[attr-defined]
    except AttributeError:
        return tp.parse_obj(val)  # type: ignore[attr-defined]
    except Exception as e:
        raise _err(path, f"pydantic validation error: {e}")

# -------------------- Entry point --------------------

def load_typed(tp: Any, val: Any, *, path: str = "$") -> Any:
    """
    Главная функция рекурсивной типо-коэрции raw→typed по аннотациям tp.
    Логирует каждый шаг и ответвление.
    """
    tp0 = tp
    tp = _strip_annotated(tp)
    origin = get_origin(tp)

    _LOG.debug("load_typed enter: path=%s, tp=%s (origin=%s), val-type=%s, val=%r",
               path, _type_name(tp), origin, type(val).__name__, val if _LOG.isEnabledFor(logging.DEBUG) else "...")

    # Any → как есть
    if tp is Any or tp is object or tp is None:
        _LOG.debug("→ Any/object/None at %s: pass-through", path)
        return val

    # Pydantic BaseModel
    if _is_base_model(tp):
        return _coerce_pydantic(val, tp, path)

    # Dataclass
    if isinstance(tp, type) and is_dataclass(tp):
        return _coerce_dataclass(val, tp, path)

    # Литералы
    if origin is t.Literal:
        return _coerce_literal(val, tp, path)

    # Union / Optional (оба варианта: typing.Union и types.UnionType)
    if origin in (t.Union, UnionType):
        return _coerce_union(val, tp, path)

    # Mapping / Sequence
    if origin in (dict, t.Dict):
        return _coerce_mapping(val, tp, path)
    if origin in (list, t.List, tuple, t.Tuple, set, t.Set):
        return _coerce_sequence(val, tp, path)

    # Enum
    if isinstance(tp, type) and issubclass(tp, Enum):
        return _coerce_enum(val, tp, path)

    # Явная поддержка NoneType вне Union (на случай прямых аннотаций)
    if tp is type(None):
        if val is None:
            _LOG.debug("NoneType at %s matched None", path)
            return None
        raise _err(path, f"expected None, got {type(val).__name__}")

    # Примитивы
    if tp in (str, int, float, bool):
        _LOG.debug("Primitive at %s: expect=%s, got=%s", path, _type_name(tp), type(val).__name__)
        if not isinstance(val, tp):
            raise _err(path, f"expected {_type_name(tp)}, got {type(val).__name__}")
        return val

    # Неизвестное — пробуем инстанцировать напрямую (на случай простых классов)
    try:
        _LOG.debug("Fallback tp(val) at %s: %s(%r)", path, _type_name(tp), val)
        return tp(val)  # type: ignore[call-arg]
    except Exception:
        _LOG.debug("Final pass-through at %s", path)
        return val
