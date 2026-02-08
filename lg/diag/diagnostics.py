from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lg.cache.fs_cache import Cache
from lg.git import is_git_repo
from lg.listing import list_sections
from lg.paths import cfg_root
from lg.template import list_contexts
from .diag_report_schema import (
    DiagReport, DiagConfig, DiagCache, DiagCheck, DiagEnv, DiagMigrationRef, DiagLastError, Severity
)
from lg.migrate import ensure_cfg_actual
from lg.migrate.errors import MigrationFatalError
from lg.migrate.version import CFG_CURRENT
from lg.protocol import PROTOCOL_VERSION
from lg.version import tool_version


def run_diag(*, rebuild_cache: bool = False) -> DiagReport:
    """
    Generates a JSON diagnostics report. Never throws exceptions externally —
    all errors are converted to "ok=False/details" or "error: str".
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

    # Section list: now try to read even WITHOUT Git, without running migrations (best-effort).
    sections: list[str] = []
    if cfg_block.exists:
        try:
            result = list_sections(root, peek=True)
            sections = [s.name for s in result.sections]
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
        # even if snapshot failed — provide a minimally meaningful block
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
    git_ok = is_git_repo(root)

    cfg_fingerprint: str | None = None
    cfg_actual: int | None = None
    applied_refs: list[DiagMigrationRef] = []

    if cfg_dir.is_dir():
        # If rebuild-cache was requested — after clearing cache run ensure_cfg_actual,
        # to restore CFG STATE. Errors are warn/error, but not fatal.
        if rebuild_cache:
            try:
                ensure_cfg_actual(cfg_dir)
            except MigrationFatalError as e:
                # error is already recorded in cfg_state, but highlight the check
                _mk("config.migrations.rebuild", Severity.warn if not git_ok else Severity.error,
                    str(e).splitlines()[0])

        # --- Migration state of lg-cfg/ ---
        try:
            state = cache.get_cfg_state(cfg_dir) or {}
            cfg_actual = int(state.get("actual", 0))
            cfg_fingerprint = state.get("fingerprint") or None
            # applied from cache
            applied_raw = state.get("applied") or []
            for item in applied_raw:
                try:
                    applied_refs.append(DiagMigrationRef(id=int(item.get("id", 0)), title=str(item.get("title", ""))))
                except Exception:
                    continue
            # last_error from cache
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
            # ignore migration subsystem issues in diagnostics
            pass

    # Fill config block with migration fields
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

    # Tokenizer libraries
    try:
        import tiktoken as _tk  # noqa: F401
        _mk("tiktoken.available", Severity.ok)
    except Exception as e:
        _mk("tiktoken.available", Severity.error, str(e))
    
    try:
        import tokenizers as _tknz  # noqa: F401
        _mk("tokenizers.available", Severity.ok)
    except Exception as e:
        _mk("tokenizers.available", Severity.warn, str(e))
    
    try:
        import sentencepiece as _sp  # noqa: F401
        _mk("sentencepiece.available", Severity.ok)
    except Exception as e:
        _mk("sentencepiece.available", Severity.warn, str(e))

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
    
    # Language adapters
    try:
        from lg.adapters.registry import list_implemented_adapters
        adapters = list_implemented_adapters()
        _mk("adapters.implemented", Severity.ok, ", ".join(adapters))
    except Exception as e:
        _mk("adapters.implemented", Severity.warn, str(e))

    # Config/migration quick hints
    if not cfg_block.exists:
        _mk("config.exists", Severity.error, str(cfg_dir))
    else:
        if cfg_block.error:
            _mk("config.load", Severity.warn, cfg_block.error)
        else:
            _mk("sections.count", Severity.ok, str(len(sections)))
        # migration summary (non-fatal if Git is missing)
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
    Builds a zip bundle with diag.json and lg-cfg/ contents.
    Returns the absolute path to the archive.
    """
    root = Path(report.root).resolve()
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    out_dir = cache.dir / "diag"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    zpath = (out_dir / f"diag-{ts}.zip").resolve()

    cfg_dir = cfg_root(root)

    with ZipFile(zpath, "w", compression=ZIP_DEFLATED) as zf:
        # diag.json (same report as in stdout)
        zf.writestr("diag.json", json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))

        # env.txt — brief summary
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

        # lg-cfg/** (if it exists)
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
                    # best-effort: skip problematic files
                    pass

        # migrations/state.json + last_error.txt (if present)
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
