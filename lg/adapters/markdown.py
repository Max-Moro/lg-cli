from __future__ import annotations

from lg.markdown import MarkdownCfg, process_markdown
from .base import BaseAdapter
from .context import LightweightContext


class MarkdownAdapter(BaseAdapter[MarkdownCfg]):
    """
    Адаптер для Markdown (.md) файлов.
    """
    name = "markdown"
    extensions = {".md"}

    def process(self, lightweight_ctx: LightweightContext):
        return process_markdown(
            lightweight_ctx.raw_text, 
            self.cfg, 
            group_size=lightweight_ctx.group_size, 
            mixed=lightweight_ctx.mixed
        )