from __future__ import annotations

import platform
import sys
from pathlib import Path

from .cache.fs_cache import Cache
from .config import load_config
from .context import list_contexts
from .config.paths import sections_path, cfg_root
from .diag_report_schema import DiagReport, DiagConfig, DiagCache, DiagCheck, DiagEnv, DiagMigrationRef
from .engine import tool_version
from .protocol import PROTOCOL_VERSION
from .migrate.version import CFG_CURRENT
from .migrate.fs import CfgFs
from .migrate.registry import get_migrations


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

    # --- Config (read-only: сначала миграционное состояние, потом, при отсутствии pending, безопасная загрузка) ---
    sec_path = sections_path(root).resolve()
    cfg_block = DiagConfig(
        exists=sec_path.is_file(),
        path=str(sec_path),
        current=CFG_CURRENT,
    )
    sections: list[str] = []
    cfg_fingerprint: str | None = None
    cfg_actual: int | None = None
    applied_refs: list[DiagMigrationRef] = []
    pending_refs: list[DiagMigrationRef] = []

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

    # --- Миграционное состояние lg-cfg/ (без применения) ---
    cfg_dir = cfg_root(root)
    git_ok = (root / ".git").is_dir()
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
            # pending — по probe() без изменений на диске
            fs = CfgFs(root, cfg_dir)
            for m in get_migrations():
                if cfg_actual is not None and m.id <= cfg_actual:
                    continue
                try:
                    needs = m.probe(fs)
                except Exception:
                    needs = False
                if needs:
                    pending_refs.append(DiagMigrationRef(id=m.id, title=getattr(m, "title", f"migration-{m.id}")))
        except Exception:
            # игнорируем проблемы миграционной подсистемы в диагностике
            pass

    # Заполняем блок config миграционными полями
    cfg_block.actual = cfg_actual
    cfg_block.fingerprint = cfg_fingerprint
    cfg_block.applied = applied_refs
    cfg_block.pending = pending_refs

    # Безопасная загрузка секций только если миграций к применению нет
    if cfg_block.exists and git_ok and len(pending_refs) == 0:
        try:
            # ВАЖНО: это вызовет ensure_cfg_actual, но pending уже пуст — изменений не будет
            cfg = load_config(root)
            sections = sorted(cfg.sections.keys())
            cfg_block.sections = sections
        except Exception as e:
            cfg_block.error = str(e)
    elif cfg_block.exists and not git_ok:
        # Вне Git не пытаемся читать конфиг (чтобы не провоцировать побочные эффекты)
        cfg_block.error = "Git repository required for safe config inspection; skipped loading to avoid implicit migrations."

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
        pend = len(pending_refs) if pending_refs else 0
        appl = len(applied_refs) if applied_refs else 0
        details = f"current={CFG_CURRENT}, actual={cfg_actual or 0}, pending={pend}, applied={appl}"
        checks.append(DiagCheck(name="config.migrations", ok=(pend == 0), details=details))

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
