"""
Context resolver for the adaptive system.

Orchestrates the full resolution of an AdaptiveModel for a context:
1. Collects all sections from context template and frontmatter
2. Resolves extends chains for each section
3. Merges adaptive data in deterministic order
4. Validates the final model
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .extends_resolver import ExtendsResolver
from ..cache.fs_cache import Cache
from ..template.analysis import SectionCollector, CollectedSections
from .model import AdaptiveModel
from .validation import AdaptiveValidator
from ..addressing import AddressingContext
from ..section import SectionService
from ..version import tool_version


@dataclass
class ContextAdaptiveData:
    """
    Result of resolving adaptive model for a context.

    Contains the merged model and metadata about the resolution.
    """
    model: AdaptiveModel
    context_name: str
    section_count: int
    validated: bool = False

    def filter_by_provider(self, provider_id: str) -> AdaptiveModel:
        """
        Return model filtered by provider.

        Content mode-sets are unchanged.
        Integration mode-set is filtered to only modes supporting provider.

        Args:
            provider_id: Provider ID to filter by

        Returns:
            Filtered AdaptiveModel
        """
        return self.model.filter_by_provider(provider_id)


class ContextResolver:
    """
    Resolver for context adaptive models.

    Brings together:
    - SectionCollector: finds all sections in context
    - ExtendsResolver: resolves section inheritance
    - AdaptiveValidator: validates business rules

    Provides caching to avoid repeated resolution.
    """

    def __init__(
        self,
        section_service: SectionService,
        addressing: AddressingContext,
        cfg_root: Path,
    ):
        """
        Initialize resolver with required services.

        Args:
            section_service: Service for section lookup/loading
            addressing: Addressing context for path resolution
            cfg_root: Root lg-cfg directory
        """
        self._section_service = section_service
        self._addressing = addressing
        self._cfg_root = cfg_root

        # Create sub-resolvers
        self._extends_resolver = ExtendsResolver(section_service)
        self._collector = SectionCollector(section_service, addressing, cfg_root)
        self._validator = AdaptiveValidator()

        # Cache: context_name -> ContextAdaptiveData
        self._cache: Dict[str, ContextAdaptiveData] = {}

    def resolve_for_context(
        self,
        context_name: str,
    ) -> ContextAdaptiveData:
        """
        Build complete AdaptiveModel for a context.

        Steps:
        1. Collect all sections from template + frontmatter
        2. Resolve extends for each section
        3. Merge adaptive data in deterministic order
        4. Validate the final model

        Args:
            context_name: Name of context (without .ctx.md suffix)

        Returns:
            ContextAdaptiveData with merged model

        Raises:
            MultipleIntegrationModeSetsError: if > 1 integration mode-set
            NoIntegrationModeSetError: if 0 integration mode-sets
        """
        # Check cache
        cache_key = f"ctx:{context_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Collect all sections
        collected = self._collector.collect(context_name)

        # Merge all sections in order
        merged_model = self._merge_collected_sections(collected)

        # Validate: contexts must have exactly one integration mode-set
        self._validator.validate_model(merged_model, context_name)

        # Build result
        result = ContextAdaptiveData(
            model=merged_model,
            context_name=context_name,
            section_count=len(collected.sections),
            validated=True,
        )

        # Cache
        self._cache[cache_key] = result

        return result

    def resolve_for_section(
        self,
        section_name: str,
        scope_dir: Optional[Path] = None,
    ) -> AdaptiveModel:
        """
        Build AdaptiveModel for standalone section render.

        Only includes this section and its extends chain.
        Sections are rendered for preview/debug, not for "Send to AI"
        which uses contexts. Integration mode-set validation is not
        performed here.

        Args:
            section_name: Section name
            scope_dir: Scope directory (defaults to cfg_root parent)

        Returns:
            AdaptiveModel for the section
        """
        if scope_dir is None:
            scope_dir = self._cfg_root.parent

        # Check cache
        cache_key = f"sec:{scope_dir}:{section_name}"
        if cache_key in self._cache:
            return self._cache[cache_key].model

        # Resolve section with extends
        resolved = self._extends_resolver.resolve(section_name, scope_dir)

        # Cache (no validation for sections)
        result = ContextAdaptiveData(
            model=resolved.adaptive_model,
            context_name=section_name,
            section_count=1,
            validated=False,
        )
        self._cache[cache_key] = result

        return resolved.adaptive_model

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._extends_resolver.clear_cache()

    def _merge_collected_sections(self, collected: CollectedSections) -> AdaptiveModel:
        """
        Merge adaptive models from all collected sections.

        Merge order:
        1. Sections from template in traversal order
        2. Sections from frontmatter includes in order

        Args:
            collected: Collected sections

        Returns:
            Merged AdaptiveModel
        """
        merged = AdaptiveModel()

        # Process sections in collection order (which is traversal order)
        for resolved_section in collected.sections:
            # Resolve extends for section
            section_data = self._extends_resolver.resolve_from_cfg(
                resolved_section.section_config,
                resolved_section.canon_key(),
                resolved_section.scope_dir,
                resolved_section.current_dir,
            )

            # Merge into result
            merged = merged.merge_with(section_data.adaptive_model)

        return merged


def create_context_resolver(
    root: Path,
    cache: Optional[Cache] = None,
) -> tuple[ContextResolver, SectionService, AddressingContext]:
    """
    Create ContextResolver with required services.

    Shared factory used by Engine and listing commands to avoid
    duplicating service initialization logic.

    Args:
        root: Repository root
        cache: Optional Cache instance (created with defaults if None)

    Returns:
        Tuple of (ContextResolver, SectionService, AddressingContext)
    """
    root = root.resolve()
    cfg_root_path = root / "lg-cfg"

    if cache is None:
        cache = Cache(root, enabled=None, fresh=False, tool_version=tool_version())

    section_service = SectionService(root, cache)
    addressing = AddressingContext(
        repo_root=root,
        initial_cfg_root=cfg_root_path,
        section_service=section_service,
    )
    resolver = ContextResolver(
        section_service=section_service,
        addressing=addressing,
        cfg_root=cfg_root_path,
    )

    return resolver, section_service, addressing


__all__ = ["ContextResolver", "ContextAdaptiveData", "create_context_resolver"]
