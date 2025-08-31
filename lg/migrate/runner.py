from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lg.cache.fs_cache import Cache
from .errors import MigrationFatalError, PreflightRequired
from .fs import CfgFs
from . import migrations  # noqa: F401  # важно: side-effect регистрации
from .registry import get_migrations
from .version import CFG_CURRENT
from ..version import tool_version


# ----------------------------- Fingerprint helpers ----------------------------- #

def _sha1_lines(lines: List[str]) -> str:
    h = hashlib.sha1()
    for ln in lines:
        h.update((ln + "\n").encode("utf-8"))
    return h.hexdigest()


def _fingerprint_cfg(repo_root: Path, cfg_root: Path) -> str:
    """
    Отпечаток текущего содержимого lg-cfg/ по рабочему дереву (tracked + untracked).
    Не опираемся на git-индекс — ловим любые правки без `git add`.
    """
    lines: list[str] = []
    base = cfg_root.resolve()
    rr = repo_root.resolve()
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        try:
            rel = p.resolve().relative_to(rr).as_posix()
        except Exception:
            # Если вдруг не внутри repo_root — используем абсолютный POSIX
            rel = p.resolve().as_posix()
        try:
            data = p.read_bytes()
        except Exception:
            data = b""
        h = hashlib.sha1(data).hexdigest()
        lines.append(f"F {h} {rel}")
    return _sha1_lines(lines)


# ----------------------------- Cache helpers ----------------------------- #

def _now_utc() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _put_state(
    cache: Cache,
    *,
    repo_root: Path,
    cfg_root: Path,
    actual: int,
    applied: List[Dict[str, Any]],
    last_error: Optional[Dict[str, Any]],
) -> None:
    """
    Единая точка записи состояния миграций в кэш.
    Обратите внимание: applied — кумулятивное множество успехов,
    не зависящее от fingerprint.
    """
    cache.put_cfg_state(
        cfg_root,
        {
            "actual": actual,
            "fingerprint": _fingerprint_cfg(repo_root, cfg_root),
            "tool": tool_version(),
            "applied": applied,
            "last_error": last_error,
            "updated_at": _now_utc(),
        },
    )


def _record_failure(
    cache: Cache,
    *,
    repo_root: Path,
    cfg_root: Path,
    actual: int,
    applied: List[Dict[str, Any]],
    migration_id: int,
    migration_title: str,
    exc: Exception | str,
    phase: str,  # "run" | "preflight"
) -> None:
    import traceback as _tb

    message = str(exc)
    tb = _tb.format_exc() if isinstance(exc, Exception) else None

    _put_state(
        cache,
        repo_root=repo_root,
        cfg_root=cfg_root,
        actual=actual,
        applied=applied,
        last_error={
            "message": message,
            "traceback": tb,
            "failed": {"id": migration_id, "title": migration_title},
            "phase": phase,
            "at": _now_utc(),
        },
    )


# ----------------------------- Misc helpers ----------------------------- #

def _git_present(repo_root: Path) -> bool:
    return (repo_root / ".git").is_dir()


def _allow_no_git() -> bool:
    val = os.environ.get("LG_MIGRATE_ALLOW_NO_GIT", "")
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _user_msg(migration_id: int, title: str, phase: str, exc: Exception | str) -> str:
    """
    Человекопонятное сообщение для пользователя в зависимости от фазы:
      • run         — ошибка выполнения миграции
      • preflight   — требуется подготовка (обычно Git/бэкап)
    """
    if phase == "run":
        action = "выполнить миграцию"
        tips = (
            "  • Выполните `lg diag --bundle` и приложите получившийся архив.\n"
            "  • Временно откатите локальные правки в `lg-cfg/` (например, `git restore -- lg-cfg/`) и повторите."
        )
    elif phase == "preflight":
        action = "начать применение миграции — требуется Git/бэкап"
        tips = (
            "  • Запустите команду внутри Git-репозитория "
            "(или инициализируйте его: `git init && git add lg-cfg && git commit -m \"init lg-cfg\"`).\n"
            "  • Затем повторите команду."
        )
    else:
        action = phase
        tips = "  • Выполните `lg diag --bundle` и приложите получившийся архив."

    return (
        f"Миграция #{migration_id} «{title}» не смогла {action}: {exc}\n\n"
        f"Что делать:\n{tips}"
    )


# ----------------------------- Public entrypoint ----------------------------- #

def ensure_cfg_actual(cfg_root: Path) -> None:
    """
    Приводит lg-cfg/ к актуальному формату:
      • сверяет кэш по отпечатку рабочего дерева;
      • запускает миграции по порядку единым методом run(fs, allow_side_effects);
      • фиксирует кумулятивную историю applied;
      • различает preflight и run-ошибки;
      • не теряет историю при смене fingerprint.
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()

    cache = Cache(repo_root, enabled=None, fresh=False, tool_version=tool_version())
    state = cache.get_cfg_state(cfg_root) or {}
    old_actual = int(state.get("actual", 0))
    old_fp = state.get("fingerprint", "")
    applied: List[Dict[str, Any]] = list(state.get("applied") or [])

    # Конфигурация новее поддерживаемой инструментом версии
    if old_actual > CFG_CURRENT:
        raise MigrationFatalError(
            f"Формат конфигурации ({old_actual}) новее версии инструмента (поддерживается до {CFG_CURRENT}).\n"
            "Обновите Listing Generator."
        )

    # Быстрый путь: отпечаток совпадает и уровень не ниже текущего, и нет last_error
    fp = _fingerprint_cfg(repo_root, cfg_root)
    if old_fp == fp and old_actual >= CFG_CURRENT and not state.get("last_error"):
        return

    # Разрешение на сайд-эффекты (готов ли бэкап / git)
    allow_side_effects = _git_present(repo_root) or _allow_no_git()

    # Пробегаем все миграции; историю успехов не обнуляем
    actual = 0
    fs = CfgFs(repo_root, cfg_root)

    # Метод сам сортирует и замораживает миграции
    for m in get_migrations():
        mid = int(m.id)
        mtitle = m.title

        try:
            changed = m.run(fs, allow_side_effects=allow_side_effects)
            actual = max(actual, mid)
            if changed:
                # добавим в кумулятивную историю успехов (без дублей по id)
                seen = {int(x.get("id", -1)) for x in applied}
                if mid not in seen:
                    applied.append(
                        {"id": mid, "title": mtitle, "at": _now_utc(), "tool": tool_version()}
                    )
            # частичная фиксация прогресса (и fingerprint) после каждой миграции
            _put_state(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                last_error=None,
            )
        except PreflightRequired as e:
            _record_failure(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                migration_id=mid,
                migration_title=mtitle,
                exc=e,
                phase="preflight",
            )
            raise MigrationFatalError(_user_msg(mid, mtitle, "preflight", e)) from e
        except Exception as e:
            _record_failure(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                migration_id=mid,
                migration_title=mtitle,
                exc=e,
                phase="run",
            )
            raise MigrationFatalError(_user_msg(mid, mtitle, "run", e)) from e

    # Финальная фиксация: «подтягиваем» до CURRENT (мегамиграции могли перепрыгнуть)
    actual = max(actual, CFG_CURRENT)
    _put_state(
        cache,
        repo_root=repo_root,
        cfg_root=cfg_root,
        actual=actual,
        applied=applied,
        last_error=None,
    )
