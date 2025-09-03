from __future__ import annotations

from lg.markdown import MarkdownCfg, process_markdown
from .base import BaseAdapter


# Тонкая оболочка над новым пайплайном lg.markdown.*


class MarkdownAdapter(BaseAdapter[MarkdownCfg]):
    """
    Адаптер для Markdown (.md) файлов.
    """
    name = "markdown"
    extensions = {".md"}

    def process(self, text: str, ext: str, group_size: int, mixed: bool):
        return process_markdown(text, self.cfg, group_size=group_size, mixed=mixed)