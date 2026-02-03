"""
Listing functions for mode-sets and tag-sets.

Provides CLI-facing API for listing adaptive configuration.
"""

from __future__ import annotations

from pathlib import Path

from .mode_sets_list_schema import ModeSetsList, ModeSet as ModeSetSchema, Mode as ModeSchema
from .tag_sets_list_schema import TagSetsList, TagSet as TagSetSchema, Tag as TagSchema
from .context_resolver import create_context_resolver
from .validation import validate_provider_support
from .errors import AdaptiveError
from .model import CLIPBOARD_PROVIDER
from ..section.service import SectionNotFoundError




def list_mode_sets(root: Path, context: str, provider: str) -> ModeSetsList:
    """
    Returns mode sets for CLI command 'list mode-sets'.

    Steps:
    1. Resolve AdaptiveModel for context via ContextResolver
    2. Filter integration mode-set by provider
    3. Return filtered mode-sets

    Args:
        root: Repository root
        context: Context name (required)
        provider: Provider ID (required)

    Returns:
        ModeSetsList with mode sets from adaptive model

    Raises:
        AdaptiveError: If context invalid or provider not supported
        FileNotFoundError: If context not found
    """
    # Create resolver
    resolver, _, _ = create_context_resolver(root)

    # Resolve adaptive model for context
    adaptive_data = resolver.resolve_for_context(context)

    # Validate provider support
    validate_provider_support(adaptive_data.model, provider, context)

    # Filter by provider
    filtered_model = adaptive_data.filter_by_provider(provider)

    # Convert to schema
    return _adaptive_model_to_mode_sets_list(filtered_model)


def _adaptive_model_to_mode_sets_list(model) -> ModeSetsList:
    """Convert AdaptiveModel to ModeSetsList schema."""
    mode_sets_list = []

    for set_id, mode_set in model.mode_sets.items():
        modes_list = []
        for mode_id, mode in mode_set.modes.items():
            # Get runs dict if present
            runs_dict = dict(mode.runs) if mode.runs else None

            mode_schema = ModeSchema(
                id=mode_id,
                title=mode.title,
                description=mode.description if mode.description else None,
                tags=list(mode.tags) if mode.tags else None,
                runs=runs_dict,
            )
            modes_list.append(mode_schema)

        mode_set_schema = ModeSetSchema(
            id=set_id,
            title=mode_set.title,
            modes=modes_list,
            integration=mode_set.is_integration
        )
        mode_sets_list.append(mode_set_schema)

    # Sort by id for stable order
    mode_sets_list.sort(key=lambda x: x.id)

    return ModeSetsList(**{"mode-sets": mode_sets_list})


def list_tag_sets(root: Path, context: str) -> TagSetsList:
    """
    Returns tag sets for CLI command 'list tag-sets'.

    Steps:
    1. Resolve AdaptiveModel for context via ContextResolver
    2. Return all tag-sets from the model

    Args:
        root: Repository root
        context: Context name (required)

    Returns:
        TagSetsList with tag sets from adaptive model

    Raises:
        AdaptiveError: If context invalid
        FileNotFoundError: If context not found
    """
    # Create resolver
    resolver, _, _ = create_context_resolver(root)

    # Resolve adaptive model for context
    adaptive_data = resolver.resolve_for_context(context)

    # Convert to schema
    return _adaptive_model_to_tag_sets_list(adaptive_data.model)


def _adaptive_model_to_tag_sets_list(model) -> TagSetsList:
    """Convert AdaptiveModel to TagSetsList schema."""
    tag_sets_list = []

    for set_id, tag_set in model.tag_sets.items():
        tags_list = []
        for tag_id, tag in tag_set.tags.items():
            tag_schema = TagSchema(
                id=tag_id,
                title=tag.title,
                description=tag.description if tag.description else None
            )
            tags_list.append(tag_schema)

        tag_set_schema = TagSetSchema(
            id=set_id,
            title=tag_set.title,
            tags=tags_list
        )
        tag_sets_list.append(tag_set_schema)

    # Sort by id for stable order
    tag_sets_list.sort(key=lambda x: x.id)

    return TagSetsList(**{"tag-sets": tag_sets_list})


def list_contexts_for_provider(root: Path, provider: str) -> list[str]:
    """
    Return contexts compatible with given provider.

    A context is compatible if its adaptive model has an integration
    mode-set with at least one mode supporting the provider.

    The clipboard provider is universally compatible — returns all contexts.

    Args:
        root: Repository root
        provider: Provider ID

    Returns:
        Sorted list of compatible context names
    """
    from ..template.common import list_contexts

    all_contexts = list_contexts(root)

    # Clipboard is universally compatible
    if provider == CLIPBOARD_PROVIDER:
        return all_contexts

    resolver, _, _ = create_context_resolver(root)
    compatible = []

    for ctx_name in all_contexts:
        try:
            adaptive_data = resolver.resolve_for_context(ctx_name)
            integration_set = adaptive_data.model.get_integration_mode_set()
            if integration_set is None:
                continue
            # Check if any mode supports this provider
            if provider in integration_set.get_supported_providers():
                compatible.append(ctx_name)
        except (AdaptiveError, SectionNotFoundError):
            # Skip contexts with resolution errors (incompatible config)
            continue

    return compatible


def list_sections_for_context(root: Path, context: str) -> list[str]:
    """
    Return sections used in given context.

    Collects all sections referenced in the context template,
    including those in conditional blocks and nested includes.
    Excludes meta-sections from frontmatter includes.

    Args:
        root: Repository root
        context: Context name (without .ctx.md suffix)

    Returns:
        Sorted list of section names (deduplicated)

    Raises:
        FileNotFoundError: If context not found
    """
    from ..template.analysis import SectionCollector

    resolver, section_service, addressing = create_context_resolver(root)
    cfg_root = root / "lg-cfg"

    collector = SectionCollector(section_service, addressing, cfg_root)
    collected = collector.collect(context)

    # Extract section names, excluding frontmatter includes (meta-sections)
    # which are used only for adaptive config, not for rendering
    section_names = set()
    frontmatter_keys = {s for s in collected.frontmatter_includes}

    for resolved in collected.sections:
        # Use the original name from template for user-friendly output
        name = resolved.name

        # Skip meta-sections from frontmatter (they don't render)
        if name in frontmatter_keys:
            continue

        # Skip addressed sections that are meta-sections
        # (sections starting with @ that are in frontmatter)
        if name.startswith('@'):
            # Check canon_key against frontmatter
            canon = resolved.canon_key()
            if any(canon.endswith(f":{fm}") or canon == f"sec:{fm}" for fm in frontmatter_keys):
                continue

        section_names.add(name)

    return sorted(section_names)


__all__ = ["list_mode_sets", "list_tag_sets", "list_contexts_for_provider", "list_sections_for_context"]
