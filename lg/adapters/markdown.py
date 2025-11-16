from __future__ import annotations

from lg.markdown import MarkdownCfg, process_markdown
from lg.markdown.templating import process_markdown_template
from .base import BaseAdapter
from .context import LightweightContext


class MarkdownAdapter(BaseAdapter[MarkdownCfg]):
    """
    Adapter for Markdown (.md) files.
    """
    name = "markdown"
    extensions = {".md"}

    def process(self, lightweight_ctx: LightweightContext):
        # Check if templating processing is needed
        if self.cfg.enable_templating and lightweight_ctx.template_ctx:
            # Apply templating before main processing
            templated_text, templating_meta = process_markdown_template(
                lightweight_ctx.raw_text,
                lightweight_ctx.template_ctx
            )
        else:
            # Use original text without templating
            templated_text = lightweight_ctx.raw_text
            templating_meta = {}

        # Apply main Markdown processing
        processed_text, markdown_meta = process_markdown(
            templated_text,
            self.cfg,
            file_label=lightweight_ctx.file_label
        )

        # Merge metadata
        combined_meta = {**templating_meta, **markdown_meta}
        
        return processed_text, combined_meta