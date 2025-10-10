"""
Рендерер секций.
"""

from __future__ import annotations

from typing import Dict, List

from ..types import LANG_NONE, ProcessedFile, RenderedSection, RenderBlock, SectionPlan


def render_section(plan: SectionPlan, processed_files: List[ProcessedFile]) -> RenderedSection:
    """
    Генерирует финальный текст и блоки.
    
    Правила:
    • use_fence=True → каждый файл в своем индивидуальном fenced-блоке ```{lang}:{path}
    • use_fence=False (только для markdown) → просто конкатенация markdown/plain без fence-блоков
    • Между блоками — один пустой абзац (двойной \n).
    """
    file_by_rel: Dict[str, ProcessedFile] = {f.rel_path: f for f in processed_files}

    out_lines: List[str] = []
    blocks: List[RenderBlock] = []

    if not plan.files:
        return RenderedSection(plan.manifest.ref, "", [], [])

    if plan.use_fence:
        # Каждый файл в своем собственном fence-блоке
        for file_entry in plan.files:
            pf = file_by_rel.get(file_entry.rel_path)
            if not pf:
                # файл отфильтрован адаптером/пропал — пропускаем
                continue
            
            # Получаем метку файла
            label = plan.labels[file_entry.rel_path]
            lang = file_entry.language_hint
            
            # Создаем fence-блок с интегрированной меткой файла
            block_lines: List[str] = []
            block_lines.append(f"```{lang}:{label}\n")
            block_lines.append(pf.processed_text.rstrip("\n"))
            block_lines.append("\n```\n")
            
            block_text = "".join(block_lines)
            blocks.append(RenderBlock(lang=lang, text=block_text, file_paths=[file_entry.rel_path]))
            out_lines.append(block_text)
            out_lines.append("\n")  # раздел между блоками
    else:
        # Markdown без fence-блоков: простая конкатенация
        block_lines: List[str] = []
        file_paths: List[str] = []
        
        for idx, file_entry in enumerate(plan.files):
            pf = file_by_rel.get(file_entry.rel_path)
            if not pf:
                continue
            file_paths.append(file_entry.rel_path)
            block_lines.append(pf.processed_text.rstrip("\n"))
            if idx < len(plan.files) - 1:
                block_lines.append("\n\n")

        block_text = "".join(block_lines)
        blocks.append(RenderBlock(lang=LANG_NONE, text=block_text, file_paths=file_paths))
        out_lines.append(block_text)

    # финальный текст
    text = "".join(out_lines).rstrip() + ("\n" if out_lines else "")

    # Создаем RenderedSection
    rendered_section = RenderedSection(
        ref=plan.manifest.ref,
        text=text,
        files=processed_files,
        blocks=blocks
    )

    return rendered_section


__all__ = ["render_section"]