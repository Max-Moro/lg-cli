"""
Плагин для обработки базовых плейсхолдеров секций и шаблонов.

Обрабатывает:
- ${section_name} - вставка секций
- ${tpl:template_name} - включение шаблонов  
- ${ctx:context_name} - включение контекстов
- Адресные ссылки @origin:name для межскоуповых включений
"""

from __future__ import annotations

from .nodes import SectionNode, IncludeNode
from .plugin import CommonPlaceholdersPlugin

__all__ = ["CommonPlaceholdersPlugin", "SectionNode", "IncludeNode"]