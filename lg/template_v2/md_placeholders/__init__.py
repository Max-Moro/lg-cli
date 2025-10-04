"""
Плагин для обработки Markdown-плейсхолдеров.

Обрабатывает:
- ${md:path} - прямое включение Markdown-файла
- ${md:path#anchor} - включение секции по заголовку
- ${md:path,level:3,strip_h1:true} - включение с параметрами
- ${md@origin:path} - адресные ссылки на файлы в других скоупах
- ${md:docs/*} - глобы для включения множества файлов
- ${md:path,if:tag:condition} - условные включения
"""

from __future__ import annotations

from .nodes import MarkdownFileNode
from .plugin import MdPlaceholdersPlugin

__all__ = ["MdPlaceholdersPlugin", "MarkdownFileNode"]
