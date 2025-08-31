from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .cache.fs_cache import Cache
from .config import list_sections_peek
from .config.paths import cfg_root
from .context import list_contexts
from .diag_report_schema import (
    DiagReport, DiagConfig, DiagCache, DiagCheck, DiagEnv, DiagMigrationRef, DiagLastError, Severity
)
from .migrate import ensure_cfg_actual
from .migrate.errors import MigrationFatalError
from .migrate.version import CFG_CURRENT
from .protocol import PROTOCOL_VERSION
from .version import tool_version


def run_diag(*, rebuild_cache: bool = False) -> DiagReport:
    """
    Формирует JSON-отчёт диагностики. Никогда не кидает наружу исключения —
    все ошибки превращаются в «ok=False/details» или «error: str».
    """
    root = Path.cwd().resolve()
    tool_ver = tool_version()

    # --- ENV / platform ---
    env = DiagEnv(
        python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        cwd=str(root),
    )

    # --- Config ---
    cfg_dir = cfg_root(root)
    cfg_block = DiagConfig(
        exists=cfg_dir.is_dir(),
        path=str(cfg_dir),
        current=CFG_CURRENT,
    )

    # Перечень секций: теперь стараемся прочитать даже БЕЗ Git, без запуска миграций (best-effort).
    sections: list[str] = []
    if cfg_block.exists:
        try:
            sections = list_sections_peek(root)
            cfg_block.sections = sections
        except Exception as e:
            cfg_block.error = str(e)

    # Contexts list
    try:
        ctxs = list_contexts(root)
    except Exception:
        ctxs = []

    # Cache block via introspection
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_ver)
    try:
        snap = cache.rebuild() if rebuild_cache else cache.snapshot()
        cache_block = DiagCache(
            enabled=snap.enabled,
            path=str(snap.path),
            exists=snap.exists,
            sizeBytes=snap.size_bytes,
            entries=snap.entries,
            rebuilt=bool(rebuild_cache),
        )
    except Exception as e:
        # даже если snapshot упал — выдаём минимально осмысленный блок
        cache_block = DiagCache(
            enabled=bool(cache.enabled),
            path=str(cache.dir),
            exists=cache.dir.exists(),
            sizeBytes=0,
            entries=0,
            rebuilt=False,
            error=str(e),
        )

    # --- Checks (best-effort) ---
    checks: list[DiagCheck] = []
    def _mk(name: str, level: Severity, details: str = "") -> None:
        checks.append(DiagCheck(name=name, level=level, details=details))

    # Cache health
    _mk("cache.enabled", Severity.ok if cache_block.enabled else Severity.warn, cache_block.path)
    _mk("cache.size", Severity.ok, f"{cache_block.sizeBytes} bytes, {cache_block.entries} entries")

    # Git
    git_ok = (root / ".git").is_dir()

    cfg_fingerprint: str | None = None
    cfg_actual: int | None = None
    applied_refs: list[DiagMigrationRef] = []

    if cfg_dir.is_dir():
        # Если просили rebuild-cache — после очистки кэша запустим ensure_cfg_actual,
        # чтобы восстановить CFG STATE. Ошибки — в warn/error, но не фатальные.
        if rebuild_cache:
            try:
                ensure_cfg_actual(cfg_dir)
            except MigrationFatalError as e:
                # ошибка уже зафиксирована в cfg_state, но подсветим чек
                _mk("config.migrations.rebuild", Severity.warn if not git_ok else Severity.error,
                    str(e).splitlines()[0])

        # --- Миграционное состояние lg-cfg/ ---
        try:
            state = cache.get_cfg_state(cfg_dir) or {}
            cfg_actual = int(state.get("actual", 0))
            cfg_fingerprint = state.get("fingerprint") or None
            # applied из кэша
            applied_raw = state.get("applied") or []
            for item in applied_raw:
                try:
                    applied_refs.append(DiagMigrationRef(id=int(item.get("id", 0)), title=str(item.get("title", ""))))
                except Exception:
                    continue
            # last_error из кэша
            if state.get("last_error"):
                le = state["last_error"]
                try:
                    cfg_block.last_error = DiagLastError(
                        message=str(le.get("message", "")),
                        traceback=le.get("traceback"),
                        failed=DiagMigrationRef(id=int(le.get("failed", {}).get("id", 0)),
                                                title=str(le.get("failed", {}).get("title", ""))) if le.get("failed") else None,
                        at=str(le.get("at") or ""),
                    )
                except Exception:
                    # best-effort
                    cfg_block.last_error = DiagLastError(message=str(state.get("last_error")))
        except Exception:
            # игнорируем проблемы миграционной подсистемы в диагностике
            pass

    # Заполняем блок config миграционными полями
    cfg_block.actual = cfg_actual
    cfg_block.fingerprint = cfg_fingerprint
    cfg_block.applied = applied_refs

    try:
        import shutil as _sh
        git_path = _sh.which("git")
        _mk("git.available", Severity.ok if git_path else Severity.warn, str(git_path or "not found in PATH"))
    except Exception as e:
        _mk("git.available", Severity.warn, str(e))
    # Git present in repo
    _mk("git.present", Severity.ok if git_ok else Severity.warn, str(root / ".git"))

    # tiktoken
    try:
        import tiktoken as _tk  # noqa: F401
        _mk("tiktoken.available", Severity.ok)
    except Exception as e:
        _mk("tiktoken.available", Severity.error, str(e))

    # Contexts/templates stats
    lgcfg = cfg_root(root)
    n_ctx = 0
    n_tpl = 0
    try:
        n_ctx = len(list(lgcfg.rglob("*.ctx.md")))
        n_tpl = len(list(lgcfg.rglob("*.tpl.md")))
    except Exception:
        pass
    _mk("contexts.count", Severity.ok, str(n_ctx))
    _mk("templates.count", Severity.ok, str(n_tpl))

    # Конфиг/миграции quick hints
    if not cfg_block.exists:
        _mk("config.exists", Severity.error, str(cfg_dir))
    else:
        if cfg_block.error:
            _mk("config.load", Severity.warn, cfg_block.error)
        else:
            _mk("sections.count", Severity.ok, str(len(sections)))
        # миграционная сводка (без фатальности при отсутствии Git)
        appl = len(applied_refs) if applied_refs else 0
        mig_level = Severity.ok
        mig_details = f"current={CFG_CURRENT}, actual={cfg_actual or 0}, applied={appl}"
        if cfg_block.last_error:
            mig_level = Severity.error
            mig_details += " (last_error present)"
        elif (cfg_actual or 0) < CFG_CURRENT:
            mig_level = Severity.warn
            mig_details += " (update recommended)"
        _mk("config.migrations", mig_level, mig_details)

    # Build report
    report = DiagReport(
        protocol=PROTOCOL_VERSION,
        tool_version=tool_ver,
        root=str(root),
        config=cfg_block,
        contexts=ctxs,
        cache=cache_block,
        checks=checks,
        env=env,
    )
    return report


# ----------------------------- Bundle builder ----------------------------- #

def _git(root: Path, args: list[str]) -> str:
    try:
        out = subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8", errors="ignore")
        return out
    except Exception:
        return ""


def build_diag_bundle(report: DiagReport) -> str:
    """
    Собирает zip-бандл с diag.json и содержимым lg-cfg/.
    Возвращает абсолютный путь к архиву.
    """
    root = Path(report.root).resolve()
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    out_dir = cache.dir / "diag"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    zpath = (out_dir / f"diag-{ts}.zip").resolve()

    cfg_dir = cfg_root(root)

    with ZipFile(zpath, "w", compression=ZIP_DEFLATED) as zf:
        # diag.json (тот же отчёт, что в stdout)
        zf.writestr("diag.json", json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))

        # env.txt — краткая сводка
        env_lines = [
            f"tool_version: {report.tool_version}",
            f"protocol: {report.protocol}",
            f"python: {report.env.python}",
            f"platform: {report.env.platform}",
            f"cwd: {report.env.cwd}",
            f"timestamp_utc: {ts}",
        ]
        zf.writestr("env.txt", "\n".join(env_lines) + "\n")

        # git info (best-effort)
        head = _git(root, ["rev-parse", "HEAD"]).strip()
        status = _git(root, ["status", "--porcelain"])
        if head:
            zf.writestr("git/head.txt", head + "\n")
        if status:
            zf.writestr("git/status.txt", status)

        # lg-cfg/** (если существует)
        if cfg_dir.is_dir():
            base = cfg_dir
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                rel = p.relative_to(base).as_posix()
                arc = f"lg-cfg/{rel}"
                try:
                    zf.write(p, arcname=arc)
                except Exception:
                    # best-effort: пропускаем проблемные файлы
                    pass

        # migrations/state.json + last_error.txt (если есть)
        try:
            cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
            state = cache.get_cfg_state(cfg_dir) or {}
            zf.writestr("migrations/state.json", json.dumps(state, ensure_ascii=False, indent=2))
            le = state.get("last_error")
            if isinstance(le, dict) and le.get("message"):
                msg = le.get("message", "")
                tb = le.get("traceback", "")
                failed = le.get("failed", {})
                mid = failed.get("id", "")
                mtitle = failed.get("title", "")
                at = le.get("at", "")
                txt = f"[{at}] migration #{mid} {mtitle}\n\n{msg}\n\n{tb}\n"
                zf.writestr("migrations/last_error.txt", txt)
        except Exception:
            # best-effort
            pass

    return str(zpath)
