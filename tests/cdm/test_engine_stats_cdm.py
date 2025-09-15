from __future__ import annotations

import os
from pathlib import Path

from lg.engine import run_report
from lg.types import RunOptions


def test_run_report_end_to_end_with_cdm(monorepo: Path):
    """
    Сквозной тест: run_report на ctx:a.
      • sectionsUsed — канонические ключи с правильными кратностями
      • totals — разумные инварианты
      • files[] — содержит пути из обеих секций
    """
    old = os.getcwd()
    os.chdir(monorepo)
    try:
        result = run_report("ctx:a", RunOptions())
    finally:
        os.chdir(old)

    # Контекстный блок
    assert result.context is not None
    assert result.context.templateName == "ctx:a"
    # Канонические ключи секций и кратности
    su = result.context.sectionsUsed
    assert su.get("packages/svc-a::a") == 2
    assert su.get("apps/web::web-api") == 1

    # Тоталы
    t = result.total
    assert t.tokensProcessed > 0
    # Обработанный текст может быть больше исходного из-за плейсхолдеров
    # Это нормальное поведение для language adapters с плейсхолдерами
    assert t.tokensRaw > 0  # просто проверяем что есть исходные токены
    assert t.renderedTokens is not None and t.renderedTokens >= 0
    # Финальный документ не меньше пайплайнового
    assert result.context.finalRenderedTokens is not None
    assert result.context.finalRenderedTokens >= t.renderedTokens
    # Template overhead — неотрицателен
    assert result.context.templateOverheadPct is not None
    assert result.context.templateOverheadPct >= 0.0

    # Файлы — хотя бы один из svc-a и один из web
    paths = [f.path for f in result.files]
    assert any(p.startswith("packages/svc-a/") for p in paths)
    assert any(p.startswith("apps/web/") for p in paths)
