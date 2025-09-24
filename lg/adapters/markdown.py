from __future__ import annotations

from lg.markdown import MarkdownCfg, process_markdown
from lg.markdown.templating import process_markdown_template
from .base import BaseAdapter
from .context import LightweightContext


class MarkdownAdapter(BaseAdapter[MarkdownCfg]):
    """
    Адаптер для Markdown (.md) файлов.
    """
    name = "markdown"
    extensions = {".md"}

    def process(self, lightweight_ctx: LightweightContext):
        # Проверяем, нужна ли обработка шаблонизации
        if self.cfg.enable_templating and lightweight_ctx.template_ctx:
            # Применяем шаблонизацию перед основной обработкой
            templated_text, templating_meta = process_markdown_template(
                lightweight_ctx.raw_text,
                lightweight_ctx.template_ctx
            )
        else:
            # Используем исходный текст без шаблонизации
            templated_text = lightweight_ctx.raw_text
            templating_meta = {}
        
        # Применяем основную обработку Markdown
        processed_text, markdown_meta = process_markdown(
            templated_text, 
            self.cfg, 
            group_size=lightweight_ctx.group_size, 
            mixed=lightweight_ctx.mixed,
            placeholder_inside_heading=self.cfg.placeholder_inside_heading
        )
        
        # Объединяем метаданные
        combined_meta = {**templating_meta, **markdown_meta}
        
        return processed_text, combined_meta