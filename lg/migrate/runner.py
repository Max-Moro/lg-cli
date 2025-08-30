from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lg.cache.fs_cache import Cache
from . import migrations  # noqa: F401  # важно импортировать для side-effect регистрации
from .errors import MigrationFatalError
from .fs import CfgFs
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
    Отпечаток содержимого lg-cfg/ с учётом Git-состояния:
      • tracked: используем вывод `git ls-files -s` (включает blob-хэши),
      • untracked: добавляем sha1 по содержимому.
    Порядок стабилен.
    """
    fs = CfgFs(repo_root, cfg_root)
    tracked = fs.git_tracked_index()          # уже POSIX
    untracked = fs.git_untracked()            # список POSIX-путей
    lines = [f"T {ln}" for ln in tracked]
    if untracked:
        # ожидается формат вида: ["U <sha1> <posix-path>", ...]
        lines.extend(fs.sha1_untracked_files(untracked))
    lines.sort()
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
    exc: Exception,
    phase: str,  # "probe" | "apply"
) -> None:
    import traceback as _tb

    _put_state(
        cache,
        repo_root=repo_root,
        cfg_root=cfg_root,
        actual=actual,  # последний успешно применённый id
        applied=applied,
        last_error={
            "message": str(exc),
            "traceback": _tb.format_exc(),
            "failed": {"id": migration_id, "title": migration_title},
            "phase": phase,
            "at": _now_utc(),
        },
    )


# ----------------------------- UX helpers ----------------------------- #

def _require_git(repo_root: Path) -> None:
    if not (repo_root / ".git").is_dir():
        raise MigrationFatalError(
            "Требуется Git-репозиторий для запуска миграций.\n"
            f"Не найден каталог: {repo_root / '.git'}"
        )


def _user_msg(migration_id: int, title: str, action: str, exc: Exception) -> str:
    # action: "проверить (probe)" | "применить (apply)"
    return (
        f"Миграция #{migration_id} «{title}» не смогла {action}: {exc}\n\n"
        "Что делать:\n"
        "  • Выполните `lg diag --bundle` и приложите получившийся архив к обращению.\n"
        "  • Временно используйте предыдущую версию LG и восстановите `lg-cfg/` из Git."
    )


# ----------------------------- Public entrypoint ----------------------------- #

def ensure_cfg_actual(cfg_root: Path) -> None:
    """
    Приводит lg-cfg/ к актуальному формату:
      • требует Git;
      • сверяет кэш по отпечатку;
      • при необходимости прогоняет миграции (строгий probe/apply);
      • фиксирует новое состояние в кэше (в т.ч. частичные успехи и последнюю ошибку).
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()
    _require_git(repo_root)

    cache = Cache(repo_root, enabled=None, fresh=False, tool_version=tool_version())
    state = cache.get_cfg_state(cfg_root)
    old_actual = int((state or {}).get("actual", 0))
    old_fp = (state or {}).get("fingerprint", "")

    # Конфигурация новее поддерживаемой инструментом версии
    if old_actual > CFG_CURRENT:
        raise MigrationFatalError(
            f"Формат конфигурации ({old_actual}) новее версии инструмента (поддерживается до {CFG_CURRENT}).\n"
            "Обновите Listing Generator."
        )

    # Быстрый путь: отпечаток совпадает и уровень не ниже текущего
    fp = _fingerprint_cfg(repo_root, cfg_root)
    if old_fp == fp and old_actual >= CFG_CURRENT:
        return

    # Если отпечаток поменялся — начинаем с нуля, иначе — с кэшированного уровня
    actual = 0 if old_fp != fp else old_actual
    applied: List[Dict[str, Any]] = []

    # Стабильный порядок миграций
    for m in sorted(get_migrations(), key=lambda x: x.id):
        mid = int(m.id)
        mtitle = getattr(m, "title", f"migration-{mid}")

        if mid <= actual:
            continue

        # Строгий probe: любые исключения — фатал с записью в кэш
        try:
            needs = m.probe(CfgFs(repo_root, cfg_root))
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
                phase="probe",
            )
            raise MigrationFatalError(_user_msg(mid, mtitle, "выполнить проверку (probe)", e)) from e

        if not needs:
            # «idle-advance»: миграция не нужна, но уровень совместимости повышаем
            actual = mid
            continue

        # Применение миграции
        try:
            m.apply(CfgFs(repo_root, cfg_root))  # идемпотентная запись на диск
            actual = mid
            applied.append({"id": mid, "title": mtitle})
            # фиксируем частичный прогресс сразу после успешной миграции
            _put_state(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                last_error=None,
            )
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
                phase="apply",
            )
            raise MigrationFatalError(_user_msg(mid, mtitle, "применить (apply)", e)) from e

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


__all__ = ["ensure_cfg_actual"]
