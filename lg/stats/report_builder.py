"""
Final report generation functions.

Transforms data from the incremental statistics collector into API v4 format.
"""

from __future__ import annotations

from .report_schema import RunResult, Total, File, Context, Scope
from ..protocol import PROTOCOL_VERSION
from ..stats.collector import StatsCollector
from ..types import TargetSpec


def build_run_result_from_collector(
    collector: StatsCollector,
    target_spec: TargetSpec
) -> RunResult:
    """
    Build RunResult from statistics collected by the collector.

    Args:
        collector: Collector with gathered statistics
        target_spec: Specification of the processed target

    Returns:
        RunResult model in API v4 format

    Raises:
        ValueError: If statistics were not collected (final texts missing)
    """
    # Get statistics from collector
    files_rows, totals, ctx_block = collector.compute_final_stats()

    # Map Totals to Total
    total = Total(
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

    # Map files to File models
    files = [
        File(
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

    # Determine scope and target
    scope = Scope.context if target_spec.kind == "context" else Scope.section
    target_norm = f"{'ctx' if target_spec.kind == 'context' else 'sec'}:{target_spec.name}"

    # Context block only for scope=context
    context: Context | None = None
    if scope is Scope.context:
        context = Context(
            templateName=ctx_block.templateName,
            sectionsUsed=dict(ctx_block.sectionsUsed),
            finalRenderedTokens=ctx_block.finalRenderedTokens,
            templateOnlyTokens=ctx_block.templateOnlyTokens,
            templateOverheadPct=ctx_block.templateOverheadPct,
            finalCtxShare=ctx_block.finalCtxShare,
        )

    # Final model
    result = RunResult(
        protocol=PROTOCOL_VERSION,
        scope=scope,
        target=target_norm,
        tokenizerLib=collector.tokenizer.lib,
        encoder=collector.tokenizer.encoder,
        ctxLimit=collector.ctx_limit,
        total=total,
        files=files,
        context=context,
    )

    return result
