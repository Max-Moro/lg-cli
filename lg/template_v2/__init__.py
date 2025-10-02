"""
Модульный шаблонизатор для Listing Generator.

Предоставляет тот же API что и lg.template, но с модульной архитектурой
на основе плагинов для лучшей расширяемости и поддерживаемости.
"""

from __future__ import annotations

from .processor import TemplateProcessor, TemplateProcessingError
from .registry import TemplateRegistry, get_registry
from .base import TemplatePlugin, ProcessingError

# Переэкспортируем все что нужно для совместимости
from ..template.context import TemplateContext

__all__ = [
    "TemplateProcessor",
    "TemplateProcessingError", 
    "TemplateContext",
    "TemplateRegistry",
    "get_registry",
    "TemplatePlugin",
    "ProcessingError",
]