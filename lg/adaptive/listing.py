"""
Listing functions for mode-sets and tag-sets.

Provides CLI-facing API for listing adaptive configuration.
"""

from __future__ import annotations

from pathlib import Path

from .mode_sets_list_schema import ModeSetsList, ModeSet as ModeSetSchema, Mode as ModeSchema
from .tag_sets_list_schema import TagSetsList, TagSet as TagSetSchema, Tag as TagSchema
from .context_resolver import ContextResolver
from .validation import validate_provider_support
from .model import CLIPBOARD_PROVIDER
from ..cache.fs_cache import Cache
from ..version import tool_version
from ..section import SectionService
from ..addressing import AddressingContext


def _create_context_resolver(root: Path) -> tuple[ContextResolver, Path]:
    """
    Create ContextResolver for list commands.

    Creates minimal services needed for adaptive model resolution
    without full Engine overhead.

    Args:
        root: Repository root

    Returns:
        Tuple of (ContextResolver, cfg_root Path)
    """
    root = root.resolve()
    cfg_root_path = root / "lg-cfg"

    # Create cache
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())

    # Create section service
    section_service = SectionService(root, cache)

    # Create addressing context
    addressing = AddressingContext(
        repo_root=root,
        initial_cfg_root=cfg_root_path,
        section_service=section_service
    )

    # Create context resolver
    resolver = ContextResolver(
        section_service=section_service,
        addressing=addressing,
        cfg_root=cfg_root_path,
    )

    return resolver, cfg_root_path


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
    resolver, _ = _create_context_resolver(root)

    # Resolve adaptive model for context
    adaptive_data = resolver.resolve_for_context(context, validate=True)

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
    resolver, _ = _create_context_resolver(root)

    # Resolve adaptive model for context
    adaptive_data = resolver.resolve_for_context(context, validate=True)

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

    resolver, _ = _create_context_resolver(root)
    compatible = []

    for ctx_name in all_contexts:
        try:
            adaptive_data = resolver.resolve_for_context(ctx_name, validate=False)
            integration_set = adaptive_data.model.get_integration_mode_set()
            if integration_set is None:
                continue
            # Check if any mode supports this provider
            if provider in integration_set.get_supported_providers():
                compatible.append(ctx_name)
        except Exception:
            # Skip contexts with resolution errors
            continue

    return compatible


__all__ = ["list_mode_sets", "list_tag_sets", "list_contexts_for_provider"]
