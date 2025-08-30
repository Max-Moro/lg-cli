from __future__ import annotations

import hashlib
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from lg.cache.fs_cache import Cache
from . import migrations  # noqa: F401  # важно импортировать для side-effect регистрации
from .fs import CfgFs
from .registry import get_migrations
from .version import CFG_CURRENT


def _sha1_lines(lines: list[str]) -> str:
    h = hashlib.sha1()
    for ln in lines:
        h.update((ln + "\n").encode("utf-8"))
    return h.hexdigest()


def _fingerprint_cfg(repo_root: Path, cfg_root: Path) -> str:
    """
    Отпечаток содержимого lg-cfg/ с учётом Git-состояния:
      • tracked: используем вывод `git ls-files -s` (включает blob-хэши),
      • untracked: добавляем sha1 по содержимому.
    Порядок стабильный.
    """
    fs = CfgFs(repo_root, cfg_root)
    tracked = fs.git_tracked_index()
    untracked = fs.git_untracked()
    lines = [f"T {ln}" for ln in tracked]
    if untracked:
        # нормализуем пути к POSIX-виду, уже приходит POSIX от git
        lines.extend(fs.sha1_untracked_files(untracked))
    lines.sort()
    return _sha1_lines(lines)


def _require_git(repo_root: Path) -> None:
    if not (repo_root / ".git").is_dir():
        raise RuntimeError(f"Listing Generator requires a Git repository. Not found: {repo_root / '.git'}")

def _tool_version() -> str:
    for dist in ("listing-generator", "lg"):
        try:
            return metadata.version(dist)
        except Exception:
            continue
    return "0.0.0"

def ensure_cfg_actual(cfg_root: Path) -> None:
    """
    Единая точка приведения lg-cfg/ к актуальному формату:
      • требуем Git;
      • сверяем кэш по отпечатку;
      • при необходимости прогоняем миграции (строгий probe/apply);
      • фиксируем новое состояние в кэше.
    """
    cfg_root = cfg_root.resolve()
    repo_root = cfg_root.parent.resolve()
    _require_git(repo_root)

    cache = Cache(repo_root, enabled=None, fresh=False, tool_version=_tool_version())
    state = cache.get_cfg_state(cfg_root)
    old_actual = int((state or {}).get("actual", 0))
    old_fp = (state or {}).get("fingerprint", "")

    # Быстрый путь: всё уже актуально и содержимое не изменилось.
    fp = _fingerprint_cfg(repo_root, cfg_root)
    if old_fp == fp and old_actual >= CFG_CURRENT:
        return

    # Миграции (если зарегистрированы)
    fs = CfgFs(repo_root, cfg_root)
    actual = max(0, old_actual)
    applied: list[dict[str, Any]] = []
    for m in get_migrations():
        if m.id <= actual:
            continue
        if not m.probe(fs):
            continue
        m.apply(fs)  # идемпотентная запись
        actual = m.id
        applied.append({"id": m.id, "title": getattr(m, "title", f"migration-{m.id}")})

    # После прогонов поднимаем до CURRENT (мегамиграции могут «перепрыгнуть»)
    actual = max(actual, CFG_CURRENT)
    # Пересчитать отпечаток (мог измениться)
    new_fp = _fingerprint_cfg(repo_root, cfg_root)
    cache.put_cfg_state(cfg_root, {
        "actual": actual,
        "fingerprint": new_fp,
        "tool": _tool_version(),
        "applied": applied,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    })

__all__ = ["ensure_cfg_actual"]
