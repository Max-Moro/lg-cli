"""
Section renderer.
"""

from __future__ import annotations

from typing import Dict, List

from ..types import LANG_NONE, ProcessedFile, RenderedSection, RenderBlock, SectionPlan


def render_section(plan: SectionPlan, processed_files: List[ProcessedFile]) -> RenderedSection:
    """
    Generates final text and blocks.

    Rules:
    • use_fence=True → each file in its own fenced block ```{lang}:{path}
    • use_fence=False (markdown only) → simple concatenation of markdown/plain without fence blocks
    • Between blocks — one empty paragraph (double \n).
    """
    file_by_rel: Dict[str, ProcessedFile] = {f.rel_path: f for f in processed_files}

    out_lines: List[str] = []
    blocks: List[RenderBlock] = []

    if not plan.files:
        return RenderedSection(plan.manifest.resolved, "", [], [])

    if plan.use_fence:
        # Each file in its own fence block
        for file_entry in plan.files:
            pf = file_by_rel.get(file_entry.rel_path)
            if not pf:
                # File filtered out by adapter/missing — skip
                continue

            # Get file label
            label = plan.labels[file_entry.rel_path]
            lang = file_entry.language_hint

            # Create fence block with integrated file label
            block_text = "".join([
                f"```{lang}:{label}\n",
                pf.processed_text.rstrip("\n"),
                "\n```\n"
            ])
            blocks.append(RenderBlock(lang=lang, text=block_text, file_paths=[file_entry.rel_path]))
            out_lines.append(block_text)
            out_lines.append("\n")  # section between blocks
    else:
        # Markdown without fence blocks: simple concatenation
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

    # Final text
    text = "".join(out_lines).rstrip() + ("\n" if out_lines else "")

    # Create RenderedSection
    rendered_section = RenderedSection(
        resolved=plan.manifest.resolved,
        text=text,
        files=processed_files,
        blocks=blocks
    )

    return rendered_section


__all__ = ["render_section"]