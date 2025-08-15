from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

# IR / API
from .types import (
    RunOptions, Diagnostics, ContextSpec, Manifest, Plan,
    ProcessedBlob, RenderedDocument, FileRow, Totals, ContextBlock
)
# pydantic JSON контракт
from .api_schema import (
    Total as TotalM,
    File as FileM,
    Context as ContextM,
    Diagnostics as DiagnosticsM,
    RunResult as RunResultM,
)

from .config.load import load_config_v6, ConfigV6
from .context.resolver import resolve_context
from .manifest.builder import build_manifest
from .plan.planner import build_plan
from .adapters import process_groups
from .render.renderer import render_document
from .stats.tokenizer import compute_stats
from .cache.fs_cache import Cache
from .vcs.git import GitVcs
from .vcs import NullVcs

@dataclass(frozen=True)
class RunContext:
    root: Path
    config: ConfigV6
    options: RunOptions
    vcs: object            # VcsProvider (GitVcs | NullVcs)
    cache: Cache
    tool_version: str = "0.0.0"
    protocol: int = 1


def run_report(name_or_sec: str, options: RunOptions) -> RunResultM:
    ctx = _bootstrap_run_context(options)
    spec: ContextSpec = resolve_context(name_or_sec, ctx)
    manifest: Manifest = build_manifest(
        root=ctx.root,
        spec=spec,
        sections_cfg=ctx.config.sections,
        mode=ctx.options.mode,
        vcs=ctx.vcs,
    )
    plan: Plan = build_plan(manifest, ctx)
    blobs: List[ProcessedBlob] = process_groups(plan, ctx)
    rendered: RenderedDocument = render_document(plan, blobs)

    files_rows, totals, ctx_block, enc_name, ctx_limit = compute_stats(
        blobs=blobs,
        rendered=rendered,
        spec=spec,
        manifest=manifest,
        model_name=options.model,
        cache=ctx.cache,
    )

    diag = Diagnostics(
        protocol=ctx.protocol,
        tool_version=ctx.tool_version,
        root=ctx.root,
        warnings=[],
    )

    return RunResultM(
        formatVersion=4,
        scope="context",
        model=options.model,
        encoder=enc_name,
        ctxLimit=ctx_limit,
        total=TotalM(**totals.__dict__),
        files=[FileM(**r.__dict__) for r in files_rows],
        context=ContextM(
            templateName=ctx_block.templateName,
            sectionsUsed=ctx_block.sectionsUsed,
            finalRenderedTokens=ctx_block.finalRenderedTokens,
            templateOnlyTokens=ctx_block.templateOnlyTokens,
            templateOverheadPct=ctx_block.templateOverheadPct,
            finalCtxShare=ctx_block.finalCtxShare,
        ),
        rendered_text=rendered.text,
        diagnostics=DiagnosticsM(
            protocol=diag.protocol,
            tool_version=diag.tool_version,
            root=str(diag.root),
            warnings=diag.warnings,
        )
    )


def run_render(name_or_sec: str, options: RunOptions) -> RenderedDocument:
    ctx = _bootstrap_run_context(options)
    spec = resolve_context(name_or_sec, ctx)
    manifest = build_manifest(
        root=ctx.root,
        spec=spec,
        sections_cfg=ctx.config.sections,
        mode=ctx.options.mode,
        vcs=ctx.vcs,
    )
    plan = build_plan(manifest, ctx)
    blobs = process_groups(plan, ctx)
    return render_document(plan, blobs)


# --------------------------- Internals --------------------------- #

def _bootstrap_run_context(options: RunOptions) -> RunContext:
    root = Path.cwd()
    cfg = load_config_v6(root)
    vcs = GitVcs() if (root / ".git").is_dir() else NullVcs()
    cache = Cache(root, tool_version="0.0.0")
    return RunContext(root=root, config=_cfg_finalize(cfg), options=options, tool_version="0.0.0", protocol=1, vcs=vcs, cache=cache)

def _cfg_finalize(cfg: ConfigV6) -> ConfigV6:
    # hook на будущее (нормализация/добавление дефолтов)
    return cfg
