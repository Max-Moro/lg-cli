from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .cache.fs_cache import Cache
from .config import load_config
from .context import list_contexts
from .config.paths import sections_path, cfg_root
from .diag_report_schema import DiagReport, DiagConfig, DiagCache, DiagCheck, DiagEnv, DiagMigrationRef, DiagLastError
from .version import tool_version
from .protocol import PROTOCOL_VERSION
from .migrate.version import CFG_CURRENT

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
    sec_path = sections_path(root).resolve()
    cfg_block = DiagConfig(
        exists=sec_path.is_file(),
        path=str(sec_path),
        current=CFG_CURRENT,
    )

    git_ok = (root / ".git").is_dir()

    # Безопасная загрузка секций
    # Во время `load_config` возможны миграции, поэтому проверяем наличие Git
    sections: list[str] = []
    if cfg_block.exists and git_ok:
        try:
            cfg = load_config(root)
            sections = sorted(cfg.sections.keys())
            cfg_block.sections = sections
        except Exception as e:
            cfg_block.error = str(e)
    elif cfg_block.exists and not git_ok:
        # Вне Git не пытаемся читать конфиг (чтобы не провоцировать побочные эффекты)
        cfg_block.error = "Git repository required for safe config inspection; skipped loading to avoid implicit migrations."

    cfg_fingerprint: str | None = None
    cfg_actual: int | None = None
    applied_refs: list[DiagMigrationRef] = []

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

    # --- Миграционное состояние lg-cfg/ ---
    cfg_dir = cfg_root(root)
    if cfg_dir.is_dir() and git_ok:
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

    # --- Checks (best-effort) ---
    checks: list[DiagCheck] = []

    # Git
    try:
        import shutil as _sh
        git_path = _sh.which("git")
        checks.append(DiagCheck(name="git.available", ok=bool(git_path), details=str(git_path or "")))
    except Exception as e:
        checks.append(DiagCheck(name="git.available", ok=False, details=str(e)))
    # Git required (по нашему контракту миграций)
    checks.append(DiagCheck(name="git.required", ok=git_ok, details=str(root / ".git")))

    # tiktoken
    try:
        import tiktoken as _tk  # noqa: F401
        checks.append(DiagCheck(name="tiktoken.available", ok=True))
    except Exception as e:
        checks.append(DiagCheck(name="tiktoken.available", ok=False, details=str(e)))

    # Contexts/templates stats
    lgcfg = cfg_root(root)
    n_ctx = 0
    n_tpl = 0
    try:
        n_ctx = len(list(lgcfg.rglob("*.ctx.md")))
        n_tpl = len(list(lgcfg.rglob("*.tpl.md")))
    except Exception:
        pass
    checks.append(DiagCheck(name="contexts.count", ok=True, details=str(n_ctx)))
    checks.append(DiagCheck(name="templates.count", ok=True, details=str(n_tpl)))

    # Конфиг/миграции quick hints
    if not cfg_block.exists:
        checks.append(DiagCheck(name="config.exists", ok=False, details=str(sec_path)))
    else:
        if cfg_block.error:
            checks.append(DiagCheck(name="config.load", ok=False, details=cfg_block.error))
        else:
            checks.append(DiagCheck(name="sections.count", ok=True, details=str(len(sections))))
        # миграционная сводка
        appl = len(applied_refs) if applied_refs else 0
        details = f"current={CFG_CURRENT}, actual={cfg_actual or 0}, applied={appl}"
        checks.append(DiagCheck(name="config.migrations", ok=(cfg_block.last_error is None), details=details))

    # Cache health
    checks.append(DiagCheck(name="cache.enabled", ok=cache_block.enabled, details=cache_block.path))
    checks.append(DiagCheck(name="cache.size", ok=True, details=f"{cache_block.sizeBytes} bytes, {cache_block.entries} entries"))

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
