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
from ..template.analysis import SectionCollector, CollectedSections
from .model import AdaptiveModel
from .validation import AdaptiveValidator
from ..addressing import AddressingContext
from ..section import SectionService


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
        validate: bool = True
    ) -> ContextAdaptiveData:
        """
        Build complete AdaptiveModel for a context.

        Steps:
        1. Collect all sections from template + frontmatter
        2. Resolve extends for each section
        3. Merge adaptive data in deterministic order
        4. Validate single integration mode-set rule (if validate=True)

        Args:
            context_name: Name of context (without .ctx.md suffix)
            validate: Whether to validate the model

        Returns:
            ContextAdaptiveData with merged model

        Raises:
            MultipleIntegrationModeSetsError: if > 1 integration mode-set
            NoIntegrationModeSetError: if 0 integration mode-sets
        """
        # Check cache
        cache_key = f"ctx:{context_name}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Re-validate if requested but not previously validated
            if validate and not cached.validated:
                self._validator.validate_model(cached.model, context_name)
                cached.validated = True
            return cached

        # Collect all sections
        collected = self._collector.collect(context_name)

        # Merge all sections in order
        merged_model = self._merge_collected_sections(collected)

        # Validate if requested
        validated = False
        if validate:
            self._validator.validate_model(merged_model, context_name)
            validated = True

        # Build result
        result = ContextAdaptiveData(
            model=merged_model,
            context_name=context_name,
            section_count=len(collected.sections),
            validated=validated,
        )

        # Cache
        self._cache[cache_key] = result

        return result

    def resolve_for_section(
        self,
        section_name: str,
        scope_dir: Optional[Path] = None,
        validate: bool = True
    ) -> AdaptiveModel:
        """
        Build AdaptiveModel for standalone section render.

        Only includes this section and its extends chain.
        Used when rendering a section directly (not via context).

        Args:
            section_name: Section name
            scope_dir: Scope directory (defaults to cfg_root parent)
            validate: Whether to validate the model

        Returns:
            AdaptiveModel for the section
        """
        if scope_dir is None:
            scope_dir = self._cfg_root.parent

        # Check cache
        cache_key = f"sec:{scope_dir}:{section_name}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if validate and not cached.validated:
                self._validator.validate_model(cached.model, section_name)
                cached.validated = True
            return cached.model

        # Resolve section with extends
        resolved = self._extends_resolver.resolve(section_name, scope_dir)

        # Validate if requested
        validated = False
        if validate:
            self._validator.validate_model(resolved.adaptive_model, section_name)
            validated = True

        # Cache
        result = ContextAdaptiveData(
            model=resolved.adaptive_model,
            context_name=section_name,
            section_count=1,
            validated=validated,
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
            )

            # Merge into result
            merged = merged.merge_with(section_data.adaptive_model)

        return merged


__all__ = ["ContextResolver", "ContextAdaptiveData"]
