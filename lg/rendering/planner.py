"""
Планировщик секции.
"""

from __future__ import annotations

from typing import List

from .labels import build_labels
from ..template.context import TemplateContext
from ..types import LANG_NONE, FileEntry, SectionManifest, SectionPlan


def build_section_plan(manifest: SectionManifest, template_ctx: TemplateContext) -> SectionPlan:
    """
    Строит план рендеринга для секции.
    
    Args:
        manifest: Манифест секции с файлами
        template_ctx: Контекст шаблона с настройками рендеринга
        
    Returns:
        План рендеринга секции
    """
    files = manifest.files
    
    if not files:
        return SectionPlan(
            manifest=manifest,
            files=[],
            md_only=True,
            use_fence=False,
            labels={}
        )
    
    # Определяем, все ли файлы - markdown/plain text
    md_only = all(f.language_hint in ("markdown", "") for f in files)
    
    # Fence-блоки используются всегда, кроме markdown
    use_fence = not md_only
    
    # Строим метки файлов
    origin = template_ctx.get_origin()
    labels = build_labels(
        (f.rel_path for f in files),
        mode=manifest.path_labels,
        origin=origin
    )
    
    return SectionPlan(
        manifest=manifest,
        files=files,
        md_only=md_only,
        use_fence=use_fence,
        labels=labels
    )





__all__ = ["build_section_plan"]