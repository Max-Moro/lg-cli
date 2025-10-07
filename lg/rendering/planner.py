"""
Планировщик секции.
"""

from __future__ import annotations

from typing import List

from .labels import build_labels
from ..template.context import TemplateContext
from ..types import LANG_NONE, FileEntry, FileGroup, SectionManifest, SectionPlan


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
            groups=[],
            md_only=True,
            use_fence=False,
            labels={}
        )
    
    # Определяем, все ли файлы - markdown/plain text
    md_only = all(f.language_hint == "" for f in files)
    
    # Fence-блоки используются всегда, кроме markdown
    use_fence = not md_only
    
    # Создаем индивидуальную группу для каждого файла
    groups = _create_individual_file_groups(files, use_fence)
    
    # Строим метки файлов
    origin = template_ctx.get_origin()
    labels = build_labels(
        (f.rel_path for f in files),
        mode=manifest.path_labels,
        origin=origin
    )
    
    return SectionPlan(
        manifest=manifest,
        groups=groups,
        md_only=md_only,
        use_fence=use_fence,
        labels=labels
    )


def _create_individual_file_groups(files: List[FileEntry], use_fence: bool) -> List[FileGroup]:
    """
    Создает индивидуальную группу для каждого файла.
    
    Args:
        files: Список файлов для группировки
        use_fence: Использовать ли fenced блоки
        
    Returns:
        Список групп файлов (по одному файлу в каждой группе)
    """
    if not files:
        return []
    
    if use_fence:
        # Каждый файл в своей собственной группе с указанием языка
        return [
            FileGroup(
                lang=f.language_hint,
                entries=[f],
                mixed=False
            )
            for f in files
        ]
    else:
        # Для markdown: одна группа без fence-блоков
        return [FileGroup(
            lang=LANG_NONE,
            entries=list(files),
            mixed=False
        )]


__all__ = ["build_section_plan"]