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
from lg.git import is_git_repo
from .errors import MigrationFatalError, PreflightRequired
from .fs import CfgFs
from . import migrations  # noqa: F401  # important: registration side-effect
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
    Fingerprint of the current lg-cfg/ content from the working tree (tracked + untracked).
    We don't rely on git index — we catch any edits without `git add`.
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
            # If somehow not inside repo_root — use absolute POSIX
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
    Single point of writing migration state to cache.
    Note: applied is a cumulative set of successes,
    independent of fingerprint.
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
    return is_git_repo(repo_root)


def _allow_no_git() -> bool:
    val = os.environ.get("LG_MIGRATE_ALLOW_NO_GIT", "")
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _user_msg(migration_id: int, title: str, phase: str, exc: Exception | str) -> str:
    """
    Human-readable message for the user depending on the phase:
      • run         — migration execution error
      • preflight   — preparation required (usually Git/backup)
    """
    if phase == "run":
        action = "execute the migration"
        tips = (
            "  • Run `diag --bundle` and attach the resulting archive.\n"
            "  • Temporarily revert local changes in `lg-cfg/` (e.g., `git restore -- lg-cfg/`) and try again."
        )
    elif phase == "preflight":
        action = "start applying the migration — Git/backup required"
        tips = (
            "  • Run the command inside a Git repository "
            "(or initialize it: `git init && git add lg-cfg && git commit -m \"init lg-cfg\"`).\n"
            "  • Then retry the command."
        )
    else:
        action = phase
        tips = "  • Run `diag --bundle` and attach the resulting archive."

    return (
        f"Migration #{migration_id} \"{title}\" could not {action}: {exc}\n\n"
        f"What to do:\n{tips}"
    )


# ----------------------------- Lock in .lg-cache (wait-based coordination) ----------------------------- #

class _MigrationLock:
    """
    Inter-process migration lock stored OUTSIDE `lg-cfg/`, under `.lg-cache/locks/`.
    • Lock name is unique for a specific cfg_root (sha1 of absolute path).
    • Created atomically (os.mkdir).
    • Respects "fresh" locks, removes "stale" ones.
    • Supports wait-based coordination: one process acquires the lock and runs migrations,
      others wait for completion with exponential backoff.
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
        # Unique name per cfg_root (same as in Cache._cfg_state_path)
        h = hashlib.sha1(str(self.cfg_root).encode("utf-8")).hexdigest()
        self.base = self.cache_dir / "locks"
        self.lock_dir = self.base / f"migrate-{h}"
        self.acquired = False

    def try_acquire(self) -> bool:
        """
        Non-blocking attempt to acquire a lock for migration execution.

        Returns:
            True if lock was successfully acquired (this process should run migrations)
            False if lock is held by another process (call wait_for_completion)

        Raises:
            MigrationFatalError: If unable to determine lock state
        """
        try:
            self.base.mkdir(parents=True, exist_ok=True)
        except Exception:
            raise MigrationFatalError(
                "Failed to create lock directory base. Check permissions for .lg-cache/"
            )

        now_ts = time.time()

        try:
            # Attempt to create lock directory atomically
            os.mkdir(self.lock_dir)
            self._write_info({"pid": os.getpid(), "started_at": _now_utc()})
            self.acquired = True
            return True

        except FileExistsError:
            # Lock already exists - check its freshness
            try:
                st = self.lock_dir.stat()
                age = now_ts - st.st_mtime

                if age <= self.stale_seconds:
                    # Fresh lock - another process is actively working
                    return False

                # Stale lock - take over
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
        Wait for lock release by another process with exponential backoff.

        Uses polling to check lock directory existence.
        When the lock disappears (released), returns control.

        Raises:
            MigrationFatalError: On wait timeout
        """
        start = time.time()
        delay = 0.05  # Initial delay 50ms
        max_delay = 1.0  # Maximum delay between checks

        while (time.time() - start) < self.wait_timeout:
            # Lock released = migrations completed
            if not self._lock_exists():
                return

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

    def release(self) -> None:
        """
        Release the lock after completion.
        Best-effort: ignores errors during deletion.
        """
        if not self.acquired:
            return

        try:
            shutil.rmtree(self.lock_dir, ignore_errors=True)
        except Exception:
            pass
        finally:
            self.acquired = False

    def _lock_exists(self) -> bool:
        """Check if lock directory exists."""
        return self.lock_dir.exists()

    def _read_info(self) -> Dict[str, Any]:
        """Read metadata from lock.json (best-effort)."""
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
    Brings lg-cfg/ to the current format with wait-based coordination:
      • Quick validity check without lock
      • Attempt to acquire lock for migration execution
      • If lock is held - wait for other process to complete migrations
      • After completion all processes continue
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()

    cache = Cache(repo_root, enabled=None, fresh=False, tool_version=tool_version())

    # Helper function to check if configuration is current
    def is_actual() -> bool:
        state = cache.get_cfg_state(cfg_root) or {}
        old_actual = int(state.get("actual", 0))
        old_fp = state.get("fingerprint", "")
        fp = _fingerprint_cfg(repo_root, cfg_root)
        return old_fp == fp and old_actual >= CFG_CURRENT and not state.get("last_error")

    # Phase 1: Quick check WITHOUT lock (fast path for parallel runs)
    if is_actual():
        return

    # Configuration is newer than tool's supported version
    state = cache.get_cfg_state(cfg_root) or {}
    old_actual = int(state.get("actual", 0))
    if old_actual > CFG_CURRENT:
        raise MigrationFatalError(
            f"Configuration format ({old_actual}) is newer than tool version (supports up to {CFG_CURRENT}).\n"
            "Please update Listing Generator."
        )

    # Phase 2: Coordination via lock
    lock = _MigrationLock(cache.dir, cfg_root)

    if lock.try_acquire():
        # I own the lock - execute migrations
        try:
            # Double-check after acquiring lock (another process might have completed migrations)
            if is_actual():
                # Configuration is already current after double-check
                return

            # Run migrations (existing logic)
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

            # Final fixation
            actual = max(actual, CFG_CURRENT)
            _put_state(
                cache,
                repo_root=repo_root,
                cfg_root=cfg_root,
                actual=actual,
                applied=applied,
                last_error=None,
            )

        finally:
            # Always release the lock
            lock.release()

    else:
        # Lock is held by another process - WAIT for migration completion
        lock.wait_for_completion()

        # After waiting, check if configuration is current
        # (in case migrations completed with an error)
        if not is_actual():
            raise MigrationFatalError(
                "Migration completed by another process, but configuration is still not actual. "
                "There may have been an error. Try running the command again."
            )
