"""
Функции формирования финального отчета для LG V2.

Преобразует данные из инкрементального коллектора статистики
в формат API v4 с обратной совместимостью.
"""

from __future__ import annotations

from typing import Tuple, Any

from ..api_schema import (
    RunResult as RunResultM, Total as TotalM, File as FileM, 
    Context as ContextM, Scope as ScopeE
)
from ..protocol import PROTOCOL_VERSION
from ..stats.collector import StatsCollector
from ..types import RunOptions
from ..types_v2 import TargetSpec


def build_run_result_from_collector(
    collector: StatsCollector,
    target_spec: TargetSpec,
    options: RunOptions
) -> RunResultM:
    """
    Строит RunResult из собранной коллектором статистики.
    
    Args:
        collector: Коллектор с собранной статистикой
        target_spec: Спецификация обработанной цели
        options: Опции выполнения
        
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

    # Мэппинг файлов в FileM
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

    # Определяем scope и target
    scope = ScopeE.context if target_spec.kind == "context" else ScopeE.section
    target_norm = f"{'ctx' if target_spec.kind == 'context' else 'sec'}:{target_spec.name}"

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
        encoder=collector.tokenizer.encoder_name,
        ctxLimit=model_info.ctx_limit,
        total=total_m,
        files=files_m,
        context=context_m,
    )
    
    return result


def create_stats_summary(collector: StatsCollector) -> dict[str, Any]:
    """
    Создает краткую сводку статистики для логирования и отладки.
    
    Args:
        collector: Коллектор статистики
        
    Returns:
        Словарь с ключевыми метриками
    """
    summary = collector.get_processing_summary()
    
    # Добавляем дополнительную информацию
    if collector.tokenizer and hasattr(collector.tokenizer, 'model_info'):
        try:
            model_info = collector.tokenizer.model_info
            summary["model_name"] = model_info.label
            summary["ctx_limit"] = model_info.ctx_limit
            summary["encoder"] = collector.tokenizer.encoder_name
            
            # Вычисляем процент использования контекста
            if summary["total_processed_tokens"] > 0 and model_info.ctx_limit > 0:
                summary["ctx_utilization_pct"] = (
                    summary["total_processed_tokens"] / model_info.ctx_limit * 100.0
                )
        except Exception:
            pass
    
    return summary


def validate_collector_state(collector: StatsCollector) -> list[str]:
    """
    Валидирует состояние коллектора перед формированием отчета.
    
    Args:
        collector: Коллектор для валидации
        
    Returns:
        Список найденных проблем (пустой, если проблем нет)
    """
    issues = []
    
    # Проверяем, что установлены итоговые тексты
    if collector.final_text is None:
        issues.append("Final text not set in collector")
    
    if collector.sections_only_text is None:
        issues.append("Sections-only text not set in collector")
    
    # Проверяем наличие статистики
    if not collector.files_stats:
        issues.append("No file statistics collected")
    
    if not collector.sections_stats:
        issues.append("No section statistics collected")
    
    # Проверяем консистентность данных
    total_files_in_sections = sum(
        len(section_stats.ref.canon_key()) 
        for section_stats in collector.sections_stats.values()
    )
    
    if total_files_in_sections == 0 and len(collector.files_stats) > 0:
        issues.append("File statistics present but no sections processed")
    
    return issues


__all__ = [
    "build_run_result_from_collector",
    "create_stats_summary", 
    "validate_collector_state"
]