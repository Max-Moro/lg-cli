"""
Рендерер секций для LG V2.

Использует новую IR-модель напрямую без конвертаций данных.
"""

from __future__ import annotations

from typing import Dict, List

from ..paths import render_file_marker
from ..types import LANG_NONE
from ..types_v2 import ProcessedFile, RenderedDocument, RenderedSection, RenderBlock, SectionPlan


def render_section(plan: SectionPlan, processed_files: List[ProcessedFile]) -> RenderedSection:
    """
    Рендерит секцию в финальный текст с новой IR-моделью.
    
    Args:
        plan: План рендеринга секции
        processed_files: Обработанные файлы
        
    Returns:
        Отрендеренная секция
    """
    # Рендерим документ
    rendered_doc = render_document_v2(plan, processed_files)
    
    # Создаем RenderedSection
    rendered_section = RenderedSection(
        ref=plan.manifest.ref,
        text=rendered_doc.text,
        files=processed_files
    )
    
    return rendered_section


def render_document_v2(plan: SectionPlan, processed_files: List[ProcessedFile]) -> RenderedDocument:
    """
    Генерирует финальный текст и блоки с новой IR-моделью.
    
    Правила аналогичны старому render_document:
    • use_fence=True → для каждой группы языка один fenced-блок ```{lang}
      и внутри — маркеры "# —— FILE: <rel> ——" перед каждым файлом.
    • use_fence=False:
        - если md_only=True → просто конкатенация markdown/plain
        - иначе → перед каждым файлом ставим маркер "# —— FILE: <rel> ——"
    • Между файлами внутри блока — один пустой абзац (двойной \n).
    """
    file_by_rel: Dict[str, ProcessedFile] = {f.rel_path: f for f in processed_files}

    out_lines: List[str] = []
    blocks: List[RenderBlock] = []

    if not plan.groups:
        return RenderedDocument(text="", blocks=[])

    if plan.use_fence:
        for group in plan.groups:
            # открываем fenced-блок
            lang = group.lang
            block_lines: List[str] = [f"```{lang}\n"]
            file_paths: List[str] = []

            for idx, file_entry in enumerate(group.entries):
                pf = file_by_rel.get(file_entry.rel_path)
                if not pf:
                    # файл отфильтрован адаптером/пропал — пропускаем
                    continue
                file_paths.append(file_entry.rel_path)
                # в fenced-блоках всегда печатаем маркер файла
                label = plan.labels.get(file_entry.rel_path) or file_entry.rel_path
                block_lines.append(render_file_marker(label))
                block_lines.append(pf.processed_text.rstrip("\n"))
                if idx < len(group.entries) - 1:
                    block_lines.append("\n\n")

            if not block_lines[-1].endswith("\n"):
                block_lines.append("\n")
            block_lines.append("```\n")
            block_text = "".join(block_lines)
            blocks.append(RenderBlock(lang=lang, text=block_text, file_paths=file_paths))
            out_lines.append(block_text)
            out_lines.append("\n")  # раздел между блоками
    else:
        # один «линейный» документ
        block_lines: List[str] = []
        file_paths: List[str] = []
        if plan.md_only:
            # чистый MD/Plain: без маркеров
            for idx, file_entry in enumerate(plan.groups[0].entries if plan.groups else []):
                pf = file_by_rel.get(file_entry.rel_path)
                if not pf:
                    continue
                file_paths.append(file_entry.rel_path)
                block_lines.append(pf.processed_text.rstrip("\n"))
                if idx < len(plan.groups[0].entries) - 1:
                    block_lines.append("\n\n")
        else:
            # смешанное/кодовое содержимое: печатаем маркер перед каждым файлом
            all_entries = []
            for group in plan.groups:
                all_entries.extend(group.entries)
            for idx, file_entry in enumerate(all_entries):
                pf = file_by_rel.get(file_entry.rel_path)
                if not pf:
                    continue
                file_paths.append(file_entry.rel_path)
                label = plan.labels.get(file_entry.rel_path) or file_entry.rel_path
                block_lines.append(render_file_marker(label))
                block_lines.append(pf.processed_text.rstrip("\n"))
                if idx < len(all_entries) - 1:
                    block_lines.append("\n\n")

        block_text = "".join(block_lines)
        blocks.append(RenderBlock(lang=LANG_NONE, text=block_text, file_paths=file_paths))
        out_lines.append(block_text)

    # финальный текст
    doc_text = "".join(out_lines).rstrip() + ("\n" if out_lines else "")
    return RenderedDocument(text=doc_text, blocks=blocks)


__all__ = ["render_section", "render_document_v2"]