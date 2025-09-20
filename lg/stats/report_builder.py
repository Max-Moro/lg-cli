"""
Функции формирования финального отчета.

Преобразует данные из инкрементального коллектора статистики в формат API v4.
"""

from __future__ import annotations

from ..api_schema import RunResult, Total, File, Context, Scope
from ..protocol import PROTOCOL_VERSION
from ..stats.collector import StatsCollector
from ..types import TargetSpec


def build_run_result_from_collector(
    collector: StatsCollector,
    target_spec: TargetSpec
) -> RunResult:
    """
    Строит RunResult из собранной коллектором статистики.
    
    Args:
        collector: Коллектор с собранной статистикой
        target_spec: Спецификация обработанной цели

    Returns:
        Модель RunResult в формате API v4
        
    Raises:
        ValueError: Если статистика не была собрана (отсутствуют итоговые тексты)
    """
    # Получаем статистику из коллектора
    files_rows, totals, ctx_block = collector.compute_final_stats()
    
    # Получаем информацию о модели
    model_info = collector.tokenizer.model_info
    
    # Мэппинг Totals в TotalM
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

    # Мэппинг файлов в FileM
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

    # Определяем scope и target
    scope = Scope.context if target_spec.kind == "context" else Scope.section
    target_norm = f"{'ctx' if target_spec.kind == 'context' else 'sec'}:{target_spec.name}"

    # Контекстный блок только для scope=context
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

    # Финальная модель
    result = RunResult(
        protocol=PROTOCOL_VERSION,
        scope=scope,
        target=target_norm,
        model=model_info.label,
        encoder=collector.tokenizer.encoder_name,
        ctxLimit=model_info.ctx_limit,
        total=total,
        files=files,
        context=context,
    )
    
    return result
