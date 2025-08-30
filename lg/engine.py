from __future__ import annotations

from pathlib import Path
from typing import Tuple

from .adapters import process_groups
from .api_schema import (
    Total as TotalM,
    File as FileM,
    Context as ContextM,
    RunResult as RunResultM,
    Scope as ScopeE,
)
from .cache.fs_cache import Cache
from .config.paths import cfg_root as cfg_root_of
from .context import resolve_context, compose_context, ComposedDocument
from .manifest import build_manifest
from .plan import build_plan
from .protocol import PROTOCOL_VERSION
from .render import render_by_section
from .run_context import RunContext
from .stats import get_model_info, compute_stats
from .types import RunOptions, RenderedDocument, ContextSpec, Manifest, ProcessedBlob
from .vcs import NullVcs
from .vcs.git import GitVcs
from .version import tool_version


# ----------------------------- helpers ----------------------------- #

def _build_run_ctx(options: RunOptions) -> RunContext:
    root = Path.cwd().resolve()
    tool_ver = tool_version()
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_ver)
    vcs = GitVcs() if (root / ".git").is_dir() else NullVcs()
    return RunContext(root=root, options=options, cache=cache, vcs=vcs)


def _pipeline_common(target: str, run_ctx: RunContext) -> Tuple[ContextSpec, Manifest, list[ProcessedBlob], ComposedDocument]:
    """
    Общая часть пайплайна для render/report.
    """
    spec = resolve_context(target, run_ctx)

    manifest = build_manifest(
        root=run_ctx.root,
        spec=spec,
        mode=run_ctx.options.mode,
        vcs=run_ctx.vcs,
    )

    plan = build_plan(manifest, run_ctx)

    blobs = process_groups(plan, run_ctx)

    rendered_by_sec = render_by_section(plan, blobs)

    composed = compose_context(
        repo_root=run_ctx.root,
        base_cfg_root=cfg_root_of(run_ctx.root),
        spec=spec,
        rendered_by_section=rendered_by_sec,
        ph2canon=spec.ph2canon,
    )

    return spec, manifest, blobs, composed


# ----------------------------- public API ----------------------------- #

def run_render(target: str, options: RunOptions) -> RenderedDocument:
    """
    Полный рендер текста (включая клей шаблонов) без вычисления JSON-отчёта.
    """
    run_ctx = _build_run_ctx(options)
    _, _, _, composed = _pipeline_common(target, run_ctx)
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
    spec, manifest, blobs, composed = _pipeline_common(target, run_ctx)

    model_info = get_model_info(run_ctx.root, options.model)
    files_rows, totals, ctx_block, enc_name = compute_stats(
        blobs=blobs,
        rendered_final_text=composed.text,
        rendered_sections_only_text=composed.sections_only_text,
        templates_hashes=composed.templates_hashes,
        spec=spec,
        manifest=manifest,
        model_info=model_info,
        code_fence=options.code_fence,
        cache=run_ctx.cache,
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

    # Определяем scope (Enum)
    scope = ScopeE.context if spec.kind == "context" else ScopeE.section
    # Единое имя цели
    target_norm = f"{'ctx' if spec.kind == 'context' else 'sec'}:{spec.name}"

    # Контекстный блок только для scope=context
    context_m: ContextM | None = None
    if scope is ScopeE.context:
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
        protocol=PROTOCOL_VERSION,
        scope=scope,
        target=target_norm,
        model=model_info.label,
        encoder=enc_name,
        ctxLimit=model_info.ctx_limit,
        total=total_m,
        files=files_m,
        context=context_m,
    )
    return result


__all__ = ["run_render", "run_report", "tool_version"]
