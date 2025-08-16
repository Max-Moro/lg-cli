from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Tuple

from .adapters.engine import process_groups
from .api_schema import (
    Total as TotalM,
    File as FileM,
    Context as ContextM,
    Diagnostics as DiagnosticsM,
    RunResult as RunResultM,
)
from .cache.fs_cache import Cache
from .config import load_config_v6, ConfigV6
from .context import resolve_context, compose_context
from .manifest.builder import build_manifest
from .plan import build_plan
from .render import render_by_section
from .stats.tokenizer import compute_stats
from .types import RunOptions, RenderedDocument, ContextSpec, Manifest, ProcessedBlob, Plan
from .vcs import VcsProvider, NullVcs
from .vcs.git import GitVcs


# ----------------------------- RunContext ----------------------------- #

@dataclass(frozen=True)
class RunContext:
    root: Path
    config: ConfigV6
    options: RunOptions
    cache: Cache
    vcs: VcsProvider


# ----------------------------- helpers ----------------------------- #

def _tool_version() -> str:
    """
    Пытаемся аккуратно достать версию инструмента.
    Падает в "0.0.0" при любых проблемах/локальном запуске.
    """
    for dist in ("listing-generator", "lg-vnext", "lg_vnext"):
        try:
            return metadata.version(dist)
        except Exception:
            continue
    return "0.0.0"


def _build_run_ctx(options: RunOptions) -> RunContext:
    root = Path.cwd().resolve()
    cfg = load_config_v6(root)
    tool_ver = _tool_version()
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_ver)
    vcs = GitVcs() if (root / ".git").is_dir() else NullVcs()
    return RunContext(root=root, config=cfg, options=options, cache=cache, vcs=vcs)


def _pipeline_common(target: str, run_ctx: RunContext) -> Tuple[ContextSpec, Manifest, Plan, list[ProcessedBlob]]:
    """
    Общая часть пайплайна для render/report:
      resolve → manifest → plan → process
    """
    # 1) resolve context/spec
    spec = resolve_context(target, run_ctx)

    # 2) build manifest (учитывает .gitignore, фильтры и режим changes)
    sections_cfg = run_ctx.config.sections  # type: ignore[attr-defined]
    manifest = build_manifest(
        root=run_ctx.root,
        spec=spec,
        sections_cfg=sections_cfg,
        mode=run_ctx.options.mode,
        vcs=run_ctx.vcs,
    )

    # 3) plan (code_fence semantics + группировка по языкам)
    plan = build_plan(manifest, run_ctx)

    # 4) adapters engine (process + cache)
    blobs = process_groups(plan, run_ctx)

    return spec, manifest, plan, blobs


# ----------------------------- public API ----------------------------- #

def run_render(target: str, options: RunOptions) -> RenderedDocument:
    """
    Полный рендер текста (включая клей шаблонов) без вычисления JSON-отчёта.
    """
    run_ctx = _build_run_ctx(options)
    spec, manifest, plan, blobs = _pipeline_common(target, run_ctx)
    rendered_by_sec = render_by_section(run_ctx, manifest, blobs)
    composed = compose_context(run_ctx.root, spec, rendered_by_sec)
    # Возвращаем итоговый текст; blocks здесь опускаем (они не отражают клей)
    return RenderedDocument(text=composed.text, blocks=[])


def run_report(target: str, options: RunOptions) -> RunResultM:
    """
    Главный вход для IDE/CLI:
      • выполняет полный пайплайн
      • считает статистику (raw/processed/rendered)
      • возвращает pydantic-модель RunResult (formatVersion=4)
    """
    run_ctx = _build_run_ctx(options)
    spec, manifest, plan, blobs = _pipeline_common(target, run_ctx)
    rendered_by_sec = render_by_section(run_ctx, manifest, blobs)
    composed = compose_context(run_ctx.root, spec, rendered_by_sec)

    files_rows, totals, ctx_block, enc_name, ctx_limit = compute_stats(
        blobs=blobs,
        rendered_final_text=composed.text,
        rendered_sections_only_text=composed.sections_only_text,
        templates_hashes=composed.templates_hashes,
        spec=spec,
        manifest=manifest,
        model_name=options.model,
        code_fence=options.code_fence,
        cache=run_ctx.cache,
    )

    # Сборка Diagnostics
    diagnostics = DiagnosticsM(
        protocol=1,
        tool_version=_tool_version(),
        root=str(run_ctx.root),
        warnings=[],
    )

    # Мэппинг Totals
    total_m = TotalM(
        sizeBytes=totals.sizeBytes,
        tokensProcessed=totals.tokensProcessed,
        tokensRaw=totals.tokensRaw,
        savedTokens=totals.savedTokens,
        savedPct=totals.savedPct,
        ctxShare=totals.ctxShare,
        renderedTokens=totals.renderedTokens,
        renderedOverheadTokens=totals.renderedOverheadTokens,
        metaSummary=dict(totals.metaSummary or {}),
    )

    # Мэппинг файлов
    files_m = [
        FileM(
            path=row.path,
            sizeBytes=row.sizeBytes,
            tokensRaw=row.tokensRaw,
            tokensProcessed=row.tokensProcessed,
            savedTokens=row.savedTokens,
            savedPct=row.savedPct,
            promptShare=row.promptShare,
            ctxShare=row.ctxShare,
            meta=dict(row.meta or {}),
        )
        for row in files_rows
    ]

    # Контекстный блок
    context_m = ContextM(
        templateName=ctx_block.templateName,
        sectionsUsed=dict(ctx_block.sectionsUsed),
        finalRenderedTokens=ctx_block.finalRenderedTokens,
        templateOnlyTokens=ctx_block.templateOnlyTokens,
        templateOverheadPct=ctx_block.templateOverheadPct,
        finalCtxShare=ctx_block.finalCtxShare,
    )

    # Финальная модель
    result = RunResultM(
        formatVersion=4,
        scope="context",
        model=options.model,
        encoder=enc_name,
        ctxLimit=ctx_limit,
        total=total_m,
        files=files_m,
        context=context_m,
        rendered_text=composed.text,
        diagnostics=diagnostics,
    )
    return result


__all__ = ["run_render", "run_report", "RunContext"]
