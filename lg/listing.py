"""
High-level listing functions for CLI introspection.

Provides orchestration layer that combines section, adaptive,
addressing and template subsystems to produce listing reports.
Extracted from section/service.py to break circular dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .adaptive.context_resolver import create_context_resolver
from .adaptive.extends_resolver import ExtendsResolver
from .adaptive.model import AdaptiveModel
from .addressing.types import ResolvedSection
from .cache.fs_cache import Cache
from .section.service import SectionService
from .section.sections_list_schema import (
    SectionsList,
    SectionInfo,
    ModeSet as ModeSetSchema,
    Mode as ModeSchema,
    TagSet as TagSetSchema,
    Tag as TagSchema,
)
from .template.analysis import SectionCollector
from .version import tool_version


def list_sections(
    root: Path,
    *,
    context: Optional[str] = None,
    peek: bool = False,
) -> SectionsList:
    """
    List sections with their adaptive configuration.

    Args:
        root: Repository root
        context: If specified, only return sections used in this context
        peek: If True, skip migrations (safe for diagnostics)

    Returns:
        SectionsList with sections and their mode-sets/tag-sets
    """
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())
    service = SectionService(root, cache)

    sections_info: List[SectionInfo] = []

    if context is not None:
        # Use resolved sections to preserve directory context
        resolved_sections = _get_resolved_sections_for_context(root, context, cache)
        for resolved in resolved_sections:
            adaptive_model = _resolve_adaptive_from_resolved(resolved, root, cache)
            # Use canonical_name for display
            section_info = _build_section_info(resolved.canonical_name, adaptive_model)
            sections_info.append(section_info)
    else:
        # Get section names from index
        if peek:
            section_names = service.list_sections_peek(root)
        else:
            section_names = service.list_sections(root)

        for name in section_names:
            adaptive_model = _resolve_section_adaptive(name, root, cache)
            section_info = _build_section_info(name, adaptive_model)
            sections_info.append(section_info)

    return SectionsList(sections=sections_info)


def _get_resolved_sections_for_context(
    root: Path, context: str, cache: Cache
) -> List[ResolvedSection]:
    """
    Get resolved sections used in a context.

    Returns only template sections (renderable), not frontmatter includes (meta).
    ResolvedSection objects preserve directory context for proper extends resolution.
    """
    _, section_service, addressing = create_context_resolver(root, cache)
    cfg_root = root / "lg-cfg"

    collector = SectionCollector(section_service, addressing, cfg_root)
    collected = collector.collect(context)

    # template_sections are already deduplicated and exclude frontmatter
    result = list(collected.template_sections)

    # Sort by canonical name for stable output
    result.sort(key=lambda r: r.canonical_name)
    return result


def _resolve_adaptive_from_resolved(
    resolved: ResolvedSection, root: Path, cache: Cache
) -> AdaptiveModel:
    """
    Resolve adaptive model from already resolved section.

    Uses ExtendsResolver.resolve_from_cfg with proper current_dir
    to correctly resolve relative extends references.
    """
    service = SectionService(root, cache)
    extends_resolver = ExtendsResolver(service)

    return extends_resolver.resolve_from_resolved(resolved).adaptive_model


def _resolve_section_adaptive(
    name: str, root: Path, cache: Cache
) -> AdaptiveModel:
    """
    Resolve adaptive model (mode-sets, tag-sets) for a section by name.

    Used when listing all sections (no context filtering).

    Returns:
        AdaptiveModel for the section
    """
    resolver, section_service, addressing = create_context_resolver(root, cache)

    # Use resolve_for_section which handles extends chain
    return resolver.resolve_for_section(name, scope_dir=root)


def _build_section_info(
    name: str, adaptive_model: AdaptiveModel
) -> SectionInfo:
    """
    Build SectionInfo schema object from section name and adaptive model.
    """
    # Convert mode-sets
    mode_sets_list: List[ModeSetSchema] = []
    for set_id, mode_set in adaptive_model.mode_sets.items():
        modes_list: List[ModeSchema] = []
        for mode_id, mode in mode_set.modes.items():
            mode_schema = ModeSchema(
                id=mode_id,
                title=mode.title,
                description=mode.description if mode.description else None,
                tags=list(mode.tags) if mode.tags else None,
                runs=dict(mode.runs) if mode.runs else None,
            )
            modes_list.append(mode_schema)

        mode_set_schema = ModeSetSchema(
            id=set_id,
            title=mode_set.title,
            modes=modes_list,
            integration=mode_set.is_integration if mode_set.is_integration else None,
        )
        mode_sets_list.append(mode_set_schema)

    # Sort mode-sets by id for stable output
    mode_sets_list.sort(key=lambda x: x.id)

    # Convert tag-sets
    tag_sets_list: List[TagSetSchema] = []
    for set_id, tag_set in adaptive_model.tag_sets.items():
        tags_list: List[TagSchema] = []
        for tag_id, tag in tag_set.tags.items():
            tag_schema = TagSchema(
                id=tag_id,
                title=tag.title,
                description=tag.description if tag.description else None,
            )
            tags_list.append(tag_schema)

        tag_set_schema = TagSetSchema(
            id=set_id,
            title=tag_set.title,
            tags=tags_list,
        )
        tag_sets_list.append(tag_set_schema)

    # Sort tag-sets by id for stable output
    tag_sets_list.sort(key=lambda x: x.id)

    return SectionInfo(
        name=name,
        **{"mode-sets": mode_sets_list, "tag-sets": tag_sets_list}
    )


__all__ = [
    "list_sections",
]
