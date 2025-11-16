"""
Section planner.
"""

from __future__ import annotations

from .labels import build_labels
from ..template.context import TemplateContext
from ..types import SectionManifest, SectionPlan


def build_section_plan(manifest: SectionManifest, template_ctx: TemplateContext) -> SectionPlan:
    """
    Builds a rendering plan for a section.

    Args:
        manifest: Section manifest with files
        template_ctx: Template context with rendering settings

    Returns:
        Section rendering plan
    """
    files = manifest.files

    if not files:
        return SectionPlan(
            manifest=manifest,
            files=[],
            use_fence=False,
            labels={}
        )

    # Fence blocks are used always, except for markdown
    use_fence = not manifest.is_doc_only

    # Build file labels
    origin = template_ctx.get_origin()
    labels = build_labels(
        (f.rel_path for f in files),
        mode=manifest.path_labels,
        origin=origin
    )

    return SectionPlan(
        manifest=manifest,
        files=files,
        use_fence=use_fence,
        labels=labels
    )





__all__ = ["build_section_plan"]