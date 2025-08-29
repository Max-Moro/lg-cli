from __future__ import annotations

from typing import Dict, List

from .renderer import render_document
from ..types import ProcessedBlob, ContextPlan, CanonSectionId


def _dedup_blobs(blobs: List[ProcessedBlob]) -> Dict[str, ProcessedBlob]:
    """Первый blob по rel_path выигрывает (стабильный порядок из Manifest)."""
    out: Dict[str, ProcessedBlob] = {}
    for b in blobs:
        if b.rel_path not in out:
            out[b.rel_path] = b
    return out


def render_by_section(plan: ContextPlan, blobs: List[ProcessedBlob]) -> Dict[CanonSectionId, str]:
    """
    Построить текст для каждой секции по заранее сформированному секционному плану.
    """
    rendered_by_sec: Dict[CanonSectionId, str] = {}
    blobs_by_rel = _dedup_blobs(blobs)

    for sec_plan in plan.sections:
        # Собираем саб-набор блобов строго в порядке, указанном в группах секции.
        file_order: List[str] = []
        for grp in sec_plan.groups:
            for fr in grp.entries:
                file_order.append(fr.rel_path)
        sub_blobs: List[ProcessedBlob] = []
        for rel in file_order:
            b = blobs_by_rel.get(rel)
            if b:
                sub_blobs.append(b)
        sub_doc = render_document(sec_plan, sub_blobs)
        rendered_by_sec[sec_plan.section_id] = sub_doc.text
    return rendered_by_sec
