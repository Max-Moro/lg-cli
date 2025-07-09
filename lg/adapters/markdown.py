from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lg.adapters.base import BaseAdapter


@dataclass
class LangMarkdown:
    """
    Конфиг для MarkdownAdapter: максимальный уровень заголовков.
    Если None — нормализация заголовков отключена.
    """
    max_heading_level: int | None = None


@BaseAdapter.register
class MarkdownAdapter(BaseAdapter):
    """
    Адаптер для Markdown (.md) файлов.
    Позволит позже реализовать нормализацию заголовков.
    """
    name = "markdown"
    extensions = {".md"}
    config_cls = LangMarkdown

    def should_skip(self, path: Path, text: str, cfg: LangMarkdown) -> bool:
        # Пока ничего не пропускаем
        return False
