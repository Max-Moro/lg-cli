from __future__ import annotations

from typing import Dict, List

from .renderer import render_document
from ..plan import build_plan
from ..types import Manifest, ProcessedBlob, FileRef


def _dedup_blobs(blobs: List[ProcessedBlob]) -> Dict[str, ProcessedBlob]:
    """Первый blob по rel_path выигрывает (стабильный порядок из Manifest)."""
    out: Dict[str, ProcessedBlob] = {}
    for b in blobs:
        if b.rel_path not in out:
            out[b.rel_path] = b
    return out


def render_by_section(run_ctx, manifest: Manifest, blobs: List[ProcessedBlob]) -> Dict[str, str]:
    """
    Построить отдельный отрендеренный текст для каждой секции, сохраняя
    порядок файлов секции из Manifest.
    """
    rendered_by_sec: Dict[str, str] = {}
    blobs_by_rel = _dedup_blobs(blobs)

    # Порядок секций — в порядке первого появления файлов секции в Manifest
    seen: Dict[str, None] = {}
    for fr in manifest.files:
        if fr.section not in seen:
            seen[fr.section] = None

    for sec in seen.keys():
        sub_files: List[FileRef] = [fr for fr in manifest.files if fr.section == sec]
        if not sub_files:
            rendered_by_sec[sec] = ""
            continue
        sub_manifest = Manifest(files=sub_files)
        sub_plan = build_plan(sub_manifest, run_ctx)
        # Подмножество blobs строго в порядке sub_manifest
        sub_blobs: List[ProcessedBlob] = []
        for fr in sub_manifest.files:
            b = blobs_by_rel.get(fr.rel_path)
            if b:
                sub_blobs.append(b)
        sub_doc = render_document(sub_plan, sub_blobs)
        rendered_by_sec[sec] = sub_doc.text
    return rendered_by_sec
