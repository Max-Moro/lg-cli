from __future__ import annotations

import platform
import sys
from pathlib import Path

from .cache.fs_cache import Cache
from .config import load_config, SCHEMA_VERSION
from .context import list_contexts
from .config.paths import sections_path, cfg_root
from .diag_report_schema import DiagReport, DiagConfig, DiagCache, DiagCheck, DiagEnv
from .engine import tool_version
from .protocol import PROTOCOL_VERSION


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
        expected_schema=SCHEMA_VERSION,
    )
    sections: list[str] = []
    if cfg_block.exists:
        try:
            cfg = load_config(root)
            cfg_block.schema_version = cfg.schema_version
            sections = sorted(cfg.sections.keys())
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

    # Git
    try:
        import shutil as _sh
        git_path = _sh.which("git")
        checks.append(DiagCheck(name="git.available", ok=bool(git_path), details=str(git_path or "")))
    except Exception as e:
        checks.append(DiagCheck(name="git.available", ok=False, details=str(e)))

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

    # Config presence/schema quick hint (if not already error)
    if not cfg_block.exists:
        checks.append(DiagCheck(name="config.exists", ok=False, details=str(sec_path)))
    else:
        if cfg_block.error:
            checks.append(DiagCheck(name="config.schema", ok=False, details=cfg_block.error))
        else:
            ok = (cfg_block.schema_version == SCHEMA_VERSION)
            details = f"schema={cfg_block.schema_version}, expected={SCHEMA_VERSION}; sections={len(sections)}"
            checks.append(DiagCheck(name="config.schema", ok=ok, details=details))
            checks.append(DiagCheck(name="sections.count", ok=True, details=str(len(sections))))

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
