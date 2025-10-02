"""
Плагин для обработки базовых плейсхолдеров секций и шаблонов.

Обрабатывает:
- ${section_name} - вставка секций
- ${tpl:template_name} - включение шаблонов  
- ${ctx:context_name} - включение контекстов
- Адресные ссылки @origin:name для межскоуповых включений
"""

from __future__ import annotations

from .plugin import CommonPlaceholdersPlugin
from .nodes import SectionNode, IncludeNode

__all__ = ["CommonPlaceholdersPlugin", "SectionNode", "IncludeNode"]