from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
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
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


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


# ----------------------------- Lock in .lg-cache (context manager) ----------------------------- #

class _MigrationLock:
    """
    Межпроцессный лок миграций, хранящийся ВНЕ `lg-cfg/`, под `.lg-cache/locks/`.
    • Имя лока уникально для конкретного cfg_root (sha1 от абсолютного пути).
    • Создаётся атомарно (os.mkdir).
    • Уважает «свежие» локи, стягивает «протухшие».
    • Гарантированно освобождается через __exit__.
    """

    def __init__(self, cache_dir: Path, cfg_root: Path, *, stale_seconds: int | None = None) -> None:
        self.cache_dir = cache_dir.resolve()
        self.cfg_root = cfg_root.resolve()
        self.stale_seconds = int(
            stale_seconds if stale_seconds is not None else os.environ.get("LG_MIGRATE_LOCK_STALE_SEC", "600")
        )
        # Уникальное имя по cfg_root (как и в Cache._cfg_state_path)
        h = hashlib.sha1(str(self.cfg_root).encode("utf-8")).hexdigest()
        self.base = self.cache_dir / "locks"
        self.lock_dir = self.base / f"migrate-{h}"
        self.acquired = False

    def __enter__(self):
        # Гарантируем наличие базы lock-папок (не сам lock!)
        try:
            self.base.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Если не смогли создать базу — лучше не рисковать параллельными миграциями
            raise MigrationFatalError("MIGRATION_IN_PROGRESS: another lg process is updating lg-cfg/")

        now_ts = time.time()
        try:
            os.mkdir(self.lock_dir)
            self._write_info({"pid": os.getpid(), "started_at": _now_utc()})
            self.acquired = True
            return self
        except FileExistsError:
            try:
                st = self.lock_dir.stat()
                if (now_ts - st.st_mtime) <= self.stale_seconds:
                    # Свежий лок — кто-то уже мигрирует
                    raise MigrationFatalError("MIGRATION_IN_PROGRESS: another lg process is updating lg-cfg/")
                # Протухший — аккуратно перехватим
                shutil.rmtree(self.lock_dir, ignore_errors=True)
                os.mkdir(self.lock_dir)
                self._write_info({"pid": os.getpid(), "recovered_at": _now_utc()})
                self.acquired = True
                return self
            except MigrationFatalError:
                raise
            except Exception:
                raise MigrationFatalError("MIGRATION_IN_PROGRESS: another lg process is updating lg-cfg/")
        except Exception:
            raise MigrationFatalError("MIGRATION_IN_PROGRESS: another lg process is updating lg-cfg/")

    def __exit__(self, exc_type, exc, tb):
        # Всегда освобождаем лок (best-effort)
        if self.acquired:
            try:
                shutil.rmtree(self.lock_dir, ignore_errors=True)
            except Exception:
                pass
        return False  # не подавляем исключения

    def _write_info(self, payload: Dict[str, Any]) -> None:
        try:
            (self.lock_dir / "lock.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass


# ----------------------------- Public entrypoint ----------------------------- #

def ensure_cfg_actual(cfg_root: Path) -> None:
    """
    Приводит lg-cfg/ к актуальному формату:
      • сверяет кэш по отпечатку рабочего дерева;
      • запускает миграции по порядку единым методом run(fs, allow_side_effects);
      • фиксирует кумулятивную историю applied;
      • различает preflight и run-ошибки;
      • не теряет историю при смене fingerprint;
      • безопасна к параллельному запуску (file-lock в .lg-cache/locks).
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

    # Быстрый путь: если отпечаток совпадает и уровень не ниже текущего, и нет last_error
    fp = _fingerprint_cfg(repo_root, cfg_root)
    if old_fp == fp and old_actual >= CFG_CURRENT and not state.get("last_error"):
        return

    # Параллельная безопасность: лок в .lg-cache/locks (вне lg-cfg/, чтобы не триггерить watcher)
    with _MigrationLock(cache.dir, cfg_root):
        # Double-check после получения лока (на случай гонки между fast-path и acquire)
        state = cache.get_cfg_state(cfg_root) or {}
        old_actual = int(state.get("actual", 0))
        old_fp = state.get("fingerprint", "")
        fp = _fingerprint_cfg(repo_root, cfg_root)
        if old_fp == fp and old_actual >= CFG_CURRENT and not state.get("last_error"):
            return

        # Разрешение на сайд-эффекты (готов ли бэкап / git)
        allow_side_effects = _git_present(repo_root) or _allow_no_git()

        # Пробегаем все миграции; историю успехов не обнуляем
        actual = 0
        fs = CfgFs(repo_root, cfg_root)

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
