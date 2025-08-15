from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

# IR / API
from .types import (
    RunOptions, Diagnostics, SectionUsage, ContextSpec, Manifest, Plan,
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

# Слои пайплайна (пока заглушки; реализация будет по PR-плану)
# from .config.load import load_config_v6
# from .context.resolver import resolve_context
# from .manifest.builder import build_manifest
# from .plan.planner import build_plan
# from .adapters import process_groups
# from .render.renderer import render_document
# from .stats.tokenizer import compute_stats
# from .cache.fs_cache import Cache

@dataclass(frozen=True)
class RunContext:
    root: Path
    # config: ConfigV6     # будет добавлено в PR-1
    options: RunOptions
    # vcs: VcsProvider     # PR-3
    # cache: Cache         # PR-5
    tool_version: str = "0.0.0"
    protocol: int = 1

# --------------------------- Orchestration --------------------------- #

def run_report(name_or_sec: str, options: RunOptions) -> RunResultM:
    """
    Главная точка входа для JSON-отчёта.
    Пока реализована как «скелет»: создаёт пустые структуры и возвращает RunResult,
    чтобы CLI мог работать на ранних PR-ах.
    """
    ctx = _bootstrap_run_context(options)

    # Заглушки стадий (будут заменены по итерациям)
    # spec: ContextSpec = resolve_context(name_or_sec, ctx)
    spec: ContextSpec = _stub_context_spec(name_or_sec)

    # manifest: Manifest = build_manifest(spec, ctx)
    manifest: Manifest = Manifest(files=[])

    # plan: Plan = build_plan(manifest, ctx)
    plan: Plan = Plan(md_only=True, use_fence=False, groups=[])

    # blobs: List[ProcessedBlob] = process_groups(plan, ctx)
    blobs: List[ProcessedBlob] = []

    # rendered: RenderedDocument = render_document(plan, blobs, ctx)
    rendered: RenderedDocument = RenderedDocument(text="", blocks=[])

    # files_rows, totals, ctx_block = compute_stats(blobs, rendered, spec, ctx)
    files_rows: List[FileRow] = []
    totals: Totals = Totals(
        sizeBytes=0, tokensProcessed=0, tokensRaw=0,
        savedTokens=0, savedPct=0.0, ctxShare=0.0,
        renderedTokens=0, renderedOverheadTokens=0, metaSummary={}
    )
    ctx_block: ContextBlock = ContextBlock(
        templateName=_ctx_display_name(spec),
        sectionsUsed=spec.sections.by_name,
        finalRenderedTokens=0, templateOnlyTokens=0, templateOverheadPct=0.0, finalCtxShare=0.0
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
        encoder="cl100k_base",
        ctxLimit=32000,
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
    """
    Рендер текстового документа.
    Пока — заглушка, возвращает пустой RenderedDocument.
    """
    # ctx = _bootstrap_run_context(options)
    # spec = resolve_context(name_or_sec, ctx)
    # manifest = build_manifest(spec, ctx)
    # plan = build_plan(manifest, ctx)
    # blobs = process_groups(plan, ctx)
    # rendered = render_document(plan, blobs, ctx)
    return RenderedDocument(text="", blocks=[])

# --------------------------- Internals (stubs) --------------------------- #

def _bootstrap_run_context(options: RunOptions) -> RunContext:
    return RunContext(root=Path.cwd(), options=options, tool_version="0.0.0", protocol=1)

def _stub_context_spec(name_or_sec: str) -> ContextSpec:
    """
    Временная заглушка ContextSpec: секция по умолчанию all или явное имя.
    """
    kind = "context"
    name = name_or_sec
    if name_or_sec.startswith("sec:"):
        kind, name = "section", name_or_sec[4:]
    elif name_or_sec.startswith("ctx:"):
        kind, name = "context", name_or_sec[4:]

    return ContextSpec(
        kind=kind, name=name, template_ast=None,
        sections=SectionUsage(by_name={name if kind == "section" else "all": 1})
    )

def _ctx_display_name(spec: ContextSpec) -> str:
    return f"{'sec' if spec.kind=='section' else 'ctx'}:{spec.name}"
