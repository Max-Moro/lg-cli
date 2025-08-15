from __future__ import annotations

from typing import Dict, List

from ..types import Plan, ProcessedBlob, RenderBlock, RenderedDocument


def render_document(plan: Plan, blobs: List[ProcessedBlob]) -> RenderedDocument:
    """
    Генерирует финальный текст и блоки.
    Правила:
      • use_fence=True → для каждой группы языка один fenced-блок ```{lang}
        и внутри — маркеры "# —— FILE: <rel> ——" перед каждым файлом.
      • use_fence=False:
          - если md_only=True → просто конкатенация markdown/plain
          - иначе → перед каждым файлом ставим маркер "# —— FILE: <rel> ——"
      • Между файлами внутри блока — один пустой абзац (двойной \n).
      • Стабильный порядок определяется Plan (он уже стабилизирован ранее).
    """
    blob_by_rel: Dict[str, ProcessedBlob] = {b.rel_path: b for b in blobs}

    out_lines: List[str] = []
    blocks: List[RenderBlock] = []

    if not plan.groups:
        return RenderedDocument(text="", blocks=[])

    if plan.use_fence:
        for grp in plan.groups:
            # открываем fenced-блок
            lang = grp.lang or ""
            block_lines: List[str] = [f"```{lang}\n"]
            file_paths: List[str] = []

            for idx, e in enumerate(grp.entries):
                b = blob_by_rel.get(e.rel_path)
                if not b:
                    # файл отфильтрован адаптером/пропал — пропускаем
                    continue
                file_paths.append(e.rel_path)
                # в fenced-блоках всегда печатаем маркер файла для читабельности
                block_lines.append(f"# —— FILE: {e.rel_path} ——\n")
                block_lines.append(b.processed_text.rstrip("\n"))
                if idx < len(grp.entries) - 1:
                    block_lines.append("\n\n")

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
            for idx, e in enumerate(plan.groups[0].entries if plan.groups else []):
                b = blob_by_rel.get(e.rel_path)
                if not b:
                    continue
                file_paths.append(e.rel_path)
                block_lines.append(b.processed_text.rstrip("\n"))
                if idx < len(plan.groups[0].entries) - 1:
                    block_lines.append("\n\n")
        else:
            # смешанное/кодовое содержимое: печатаем маркер перед каждым файлом
            all_entries = []
            for grp in plan.groups:
                all_entries.extend(grp.entries)
            for idx, e in enumerate(all_entries):
                b = blob_by_rel.get(e.rel_path)
                if not b:
                    continue
                file_paths.append(e.rel_path)
                block_lines.append(f"# —— FILE: {e.rel_path} ——\n")
                block_lines.append(b.processed_text.rstrip("\n"))
                if idx < len(all_entries) - 1:
                    block_lines.append("\n\n")

        block_text = "".join(block_lines)
        blocks.append(RenderBlock(lang="", text=block_text, file_paths=file_paths))
        out_lines.append(block_text)

    # финальный текст
    doc_text = "".join(out_lines).rstrip() + ("\n" if out_lines else "")
    return RenderedDocument(text=doc_text, blocks=blocks)
