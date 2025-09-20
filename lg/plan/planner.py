"""
Планировщик секции для LG V2.

Заменяет части старого build_plan, но работает с одной секцией
и использует новую IR-модель типов.
"""

from __future__ import annotations

from typing import List

from ..paths import build_labels
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
    
    # Определяем, использовать ли fenced блоки
    use_fence = template_ctx.current_state.mode_options.code_fence and not md_only
    
    # Группируем файлы по языку
    groups = _group_files_by_language(files, use_fence)
    
    # Строим метки файлов
    labels = build_labels(
        (f.rel_path for f in files),
        mode=manifest.path_labels
    )
    
    return SectionPlan(
        manifest=manifest,
        groups=groups,
        md_only=md_only,
        use_fence=use_fence,
        labels=labels
    )


def _group_files_by_language(files: List[FileEntry], use_fence: bool) -> List[FileGroup]:
    """
    Группирует файлы по языку для рендеринга.
    
    Args:
        files: Список файлов для группировки
        use_fence: Использовать ли fenced блоки
        
    Returns:
        Список групп файлов
    """
    if not files:
        return []
    
    if use_fence:
        # Группируем по языкам для fenced блоков
        groups = []
        current_lang = files[0].language_hint
        current_group = [files[0]]
        
        for f in files[1:]:
            if f.language_hint == current_lang:
                current_group.append(f)
            else:
                groups.append(FileGroup(
                    lang=current_lang,
                    entries=current_group,
                    mixed=False
                ))
                current_lang = f.language_hint
                current_group = [f]
        
        # Добавляем последнюю группу
        groups.append(FileGroup(
            lang=current_lang,
            entries=current_group,
            mixed=False
        ))
        
        return groups
    else:
        # Одна группа без языка
        languages = {f.language_hint for f in files}
        mixed = len(languages) > 1
        
        return [FileGroup(
            lang=LANG_NONE,  # Пустой язык для смешанного контента
            entries=list(files),
            mixed=mixed
        )]


__all__ = ["build_section_plan"]