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
    phase: str,  # "probe" | "apply" | "preflight"
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


# —— in lg/migrate/runner.py ——

def _user_msg(migration_id: int, title: str, phase: str, exc: Exception | str) -> str:
    """
    Человекопонятное сообщение для пользователя в зависимости от фазы:
      • probe       — проверка совместимости
      • apply       — применение изменений
      • preflight   — подготовки к применению (например, требуется Git)
    """
    if phase == "probe":
        action = "выполнить проверку совместимости (probe)"
        tips = (
            "  • Выполните `lg diag --bundle` и приложите получившийся архив.\n"
            "  • При необходимости восстановите `lg-cfg/` из Git и повторите команду."
        )
    elif phase == "apply":
        action = "применить изменения (apply)"
        tips = (
            "  • Выполните `lg diag --bundle` и приложите получившийся архив.\n"
            "  • Временно откатите локальные правки в `lg-cfg/` (например, `git restore -- lg-cfg/`) и повторите."
        )
    elif phase == "preflight":
        action = "начать применение миграции — требуется Git"
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
      • выполняет строгий probe() без требований к Git;
      • требует Git ТОЛЬКО если нужно реально применять миграцию;
      • фиксирует частичный прогресс и ошибки (probe/apply/preflight) в кэше.
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()

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

    fs = CfgFs(repo_root, cfg_root)

    # Стабильный порядок миграций
    for m in sorted(get_migrations(), key=lambda x: x.id):
        mid = int(m.id)
        mtitle = getattr(m, "title", f"migration-{mid}")

        if mid <= actual:
            continue

        # Строгий probe: любые исключения — фатал с записью в кэш
        try:
            needs = m.probe(fs)
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
            raise MigrationFatalError(_user_msg(mid, mtitle, "probe", e)) from e

        if not needs:
            # «idle-advance»: миграция не нужна, но уровень совместимости повышаем
            actual = mid
            continue

        # Перед применением — требуем Git. Если его нет, аккуратно фиксируем preflight и подсказываем пользователю.
        if not _git_present(repo_root):
            msg = f"Требуется Git-репозиторий для применения миграций. Не найден каталог: {repo_root / '.git'}"
            _record_failure(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                migration_id=mid,
                migration_title=mtitle,
                exc=msg,
                phase="preflight",
            )
            raise MigrationFatalError(_user_msg(mid, mtitle, "preflight", msg))

        # Применение миграции
        try:
            m.apply(fs)  # идемпотентная запись на диск
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
            raise MigrationFatalError(_user_msg(mid, mtitle, "apply", e)) from e

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
