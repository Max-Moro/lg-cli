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


# ----------------------------- Lock in .lg-cache (wait-based coordination) ----------------------------- #

class _MigrationLock:
    """
    Межпроцессный лок миграций, хранящийся ВНЕ `lg-cfg/`, под `.lg-cache/locks/`.
    • Имя лока уникально для конкретного cfg_root (sha1 от абсолютного пути).
    • Создаётся атомарно (os.mkdir).
    • Уважает «свежие» локи, стягивает «протухшие».
    • Поддерживает wait-based coordination: один процесс захватывает лок и выполняет миграции,
      остальные ждут завершения с exponential backoff.
    """

    def __init__(
        self,
        cache_dir: Path,
        cfg_root: Path,
        *,
        stale_seconds: int | None = None,
        wait_timeout: int | None = None
    ) -> None:
        self.cache_dir = cache_dir.resolve()
        self.cfg_root = cfg_root.resolve()
        self.stale_seconds = int(
            stale_seconds if stale_seconds is not None
            else os.environ.get("LG_MIGRATE_LOCK_STALE_SEC", "120")
        )
        self.wait_timeout = int(
            wait_timeout if wait_timeout is not None
            else os.environ.get("LG_MIGRATE_WAIT_TIMEOUT", "180")
        )
        # Уникальное имя по cfg_root (как и в Cache._cfg_state_path)
        h = hashlib.sha1(str(self.cfg_root).encode("utf-8")).hexdigest()
        self.base = self.cache_dir / "locks"
        self.lock_dir = self.base / f"migrate-{h}"
        self.acquired = False
        self.completed_marker = self.lock_dir / "completed.marker"

    def try_acquire(self) -> bool:
        """
        Неблокирующая попытка захватить лок для выполнения миграций.

        Returns:
            True если лок успешно захвачен (этот процесс должен выполнить миграции)
            False если лок занят другим процессом (нужно вызвать wait_for_completion)

        Raises:
            MigrationFatalError: При невозможности определить состояние лока
        """
        try:
            self.base.mkdir(parents=True, exist_ok=True)
        except Exception:
            raise MigrationFatalError(
                "Failed to create lock directory base. Check permissions for .lg-cache/"
            )

        now_ts = time.time()

        try:
            # Попытка создать директорию лока атомарно
            os.mkdir(self.lock_dir)
            self._write_info({"pid": os.getpid(), "started_at": _now_utc()})
            self.acquired = True
            return True

        except FileExistsError:
            # Лок уже существует - проверяем его свежесть
            try:
                st = self.lock_dir.stat()
                age = now_ts - st.st_mtime

                if age <= self.stale_seconds:
                    # Свежий лок - другой процесс активно работает
                    return False

                # Протухший лок - перехватываем
                info = self._read_info()
                old_pid = info.get("pid", "unknown")

                shutil.rmtree(self.lock_dir, ignore_errors=True)
                os.mkdir(self.lock_dir)
                self._write_info({
                    "pid": os.getpid(),
                    "recovered_at": _now_utc(),
                    "recovered_from_pid": old_pid
                })
                self.acquired = True
                return True

            except Exception as e:
                raise MigrationFatalError(
                    f"Failed to check migration lock state: {e}"
                )

        except Exception as e:
            raise MigrationFatalError(
                f"Failed to acquire migration lock: {e}"
            )

    def wait_for_completion(self) -> None:
        """
        Ожидает завершения миграций другим процессом с exponential backoff.

        Использует polling для проверки появления completed.marker.
        После успешного завершения возвращает управление, позволяя
        процессу продолжить работу.

        Raises:
            MigrationFatalError: При timeout или неожиданном исчезновении лока
        """
        start = time.time()
        delay = 0.05  # Начальная задержка 50ms
        max_delay = 1.0  # Максимальная задержка между проверками

        while (time.time() - start) < self.wait_timeout:
            # Проверка 1: Миграции завершены успешно
            if self._is_completed():
                return

            # Проверка 2: Лок исчез (процесс-владелец упал?)
            if not self._lock_exists():
                # Double-check через небольшую задержку
                time.sleep(0.1)
                if self._is_completed():
                    return
                # Лок исчез без маркера завершения - возможно crash
                raise MigrationFatalError(
                    "Migration lock disappeared without completion marker. "
                    "Previous migration process may have crashed. "
                    "Try running the command again."
                )

            # Exponential backoff
            time.sleep(delay)
            delay = min(delay * 1.5, max_delay)

        # Timeout
        info = self._read_info()
        owner_pid = info.get("pid", "unknown")
        started_at = info.get("started_at", "unknown")

        raise MigrationFatalError(
            f"Timeout waiting for migration completion ({self.wait_timeout}s). "
            f"Lock owner: PID {owner_pid}, started at {started_at}. "
            f"If the process is stuck, manually remove: {self.lock_dir}"
        )

    def mark_completed(self) -> None:
        """
        Создает маркер успешного завершения миграций.
        Должен вызваться владельцем лока после успешного выполнения всех миграций.
        """
        if not self.acquired:
            return

        try:
            self.completed_marker.write_text(
                json.dumps({
                    "pid": os.getpid(),
                    "completed_at": _now_utc(),
                }, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            # Best-effort: если не удалось создать маркер, не критично
            # Ждущие процессы увидят что лок освобожден и сделают свою проверку
            pass

    def release(self) -> None:
        """
        Освобождает лок после завершения работы.
        Best-effort: игнорирует ошибки при удалении.
        """
        if not self.acquired:
            return

        try:
            shutil.rmtree(self.lock_dir, ignore_errors=True)
        except Exception:
            pass
        finally:
            self.acquired = False

    def _is_completed(self) -> bool:
        """Проверяет наличие маркера завершения миграций."""
        return self.completed_marker.exists()

    def _lock_exists(self) -> bool:
        """Проверяет существование директории лока."""
        return self.lock_dir.exists()

    def _read_info(self) -> Dict[str, Any]:
        """Читает метаданные из lock.json (best-effort)."""
        try:
            return json.loads((self.lock_dir / "lock.json").read_text(encoding="utf-8"))
        except Exception:
            return {}

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
    Приводит lg-cfg/ к актуальному формату с wait-based coordination:
      • Быстрая проверка актуальности без лока
      • Попытка захватить лок для выполнения миграций
      • Если лок занят - ожидание завершения миграций другим процессом
      • После завершения все процессы продолжают работу
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()

    cache = Cache(repo_root, enabled=None, fresh=False, tool_version=tool_version())

    # Вспомогательная функция для проверки актуальности
    def is_actual() -> bool:
        state = cache.get_cfg_state(cfg_root) or {}
        old_actual = int(state.get("actual", 0))
        old_fp = state.get("fingerprint", "")
        fp = _fingerprint_cfg(repo_root, cfg_root)
        return old_fp == fp and old_actual >= CFG_CURRENT and not state.get("last_error")

    # Фаза 1: Быстрая проверка БЕЗ лока (fast path для параллельных запусков)
    if is_actual():
        return

    # Конфигурация новее поддерживаемой инструментом версии
    state = cache.get_cfg_state(cfg_root) or {}
    old_actual = int(state.get("actual", 0))
    if old_actual > CFG_CURRENT:
        raise MigrationFatalError(
            f"Формат конфигурации ({old_actual}) новее версии инструмента (поддерживается до {CFG_CURRENT}).\n"
            "Обновите Listing Generator."
        )

    # Фаза 2: Координация через лок
    lock = _MigrationLock(cache.dir, cfg_root)

    if lock.try_acquire():
        # Я владелец лока - выполняю миграции
        try:
            # Double-check после захвата лока (другой процесс мог завершить миграции)
            if is_actual():
                lock.mark_completed()
                return

            # Выполнение миграций (существующая логика)
            state = cache.get_cfg_state(cfg_root) or {}
            applied: List[Dict[str, Any]] = list(state.get("applied") or [])

            allow_side_effects = _git_present(repo_root) or _allow_no_git()

            actual = 0
            fs = CfgFs(repo_root, cfg_root)

            for m in get_migrations():
                mid = int(m.id)
                mtitle = m.title

                try:
                    changed = m.run(fs, allow_side_effects=allow_side_effects)
                    actual = max(actual, mid)
                    if changed:
                        seen = {int(x.get("id", -1)) for x in applied}
                        if mid not in seen:
                            applied.append(
                                {"id": mid, "title": mtitle, "at": _now_utc(), "tool": tool_version()}
                            )
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

            # Финальная фиксация
            actual = max(actual, CFG_CURRENT)
            _put_state(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                last_error=None,
            )

            # Сигнализируем об успешном завершении
            lock.mark_completed()

        finally:
            # Всегда освобождаем лок
            lock.release()

    else:
        # Лок занят другим процессом - ЖДЕМ завершения миграций
        lock.wait_for_completion()

        # После завершения ожидания проверяем актуальность
        # (на случай если миграции завершились с ошибкой)
        if not is_actual():
            raise MigrationFatalError(
                "Migration completed by another process, but configuration is still not actual. "
                "There may have been an error. Try running the command again."
            )
