"""
Модульный шаблонизатор для Listing Generator.

Предоставляет тот же API что и lg.template, но с модульной архитектурой
на основе плагинов для лучшей расширяемости и поддерживаемости.
"""

from __future__ import annotations

from .processor import TemplateProcessor, TemplateProcessingError, create_v2_template_processor
# Переэкспортируем все что нужно для совместимости
from ..template.context import TemplateContext

__all__ = [
    "TemplateProcessor",
    "TemplateProcessingError", 
    "TemplateContext",
    "create_v2_template_processor",
]