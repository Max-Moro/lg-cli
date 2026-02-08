"""
Extends resolver for the adaptive system.

Resolves section inheritance chains with:
- Cycle detection
- Deterministic merge order (depth-first, left-to-right)
- Proper merge semantics per field type
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .errors import ExtendsCycleError, SectionNotFoundInExtendsError
from .model import AdaptiveModel
from .section_extractor import extract_adaptive_model
from ..section.model import SectionCfg, AdapterConfig
from ..section.service import SectionService
from ..section.errors import SectionNotFoundError
from ..addressing.types import ResolvedSection


@dataclass
class ResolvedSectionData:
    """
    Result of resolving a section with all extends applied.

    Contains merged adaptive model and configuration fields,
    while preserving access to original filters/targets.
    """
    adaptive_model: AdaptiveModel
    extensions: List[str]
    adapters: Dict[str, AdapterConfig]
    skip_empty: bool
    path_labels: str
    # Original config for non-inherited fields (filters, targets)
    original_cfg: Optional[SectionCfg] = None


class ExtendsResolver:
    """
    Resolver for section inheritance chains.

    Handles:
    - Cycle detection via resolution stack
    - Depth-first, left-to-right traversal of extends
    - Proper merge semantics for each field type
    - Addressed section references (@scope:name)
    - Caching of resolved sections
    """

    def __init__(self, section_service: SectionService):
        """
        Initialize resolver with section service.

        Args:
            section_service: Service for finding and loading sections
        """
        self._section_service = section_service
        self._resolution_stack: List[str] = []
        self._cache: Dict[str, ResolvedSectionData] = {}

    def resolve(
        self,
        section_name: str,
        scope_dir: Path,
        current_dir: str = ""
    ) -> ResolvedSectionData:
        """
        Resolve section with all extends applied.

        Args:
            section_name: Section name (may include @scope:name)
            scope_dir: Current scope directory
            current_dir: Current directory for relative resolution

        Returns:
            ResolvedSectionData with merged configuration

        Raises:
            ExtendsCycleError: If circular dependency detected
            SectionNotFoundInExtendsError: If referenced section not found
        """
        # Build canonical key for caching
        cache_key = self._build_cache_key(section_name, scope_dir)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check for cycles
        if cache_key in self._resolution_stack:
            cycle = self._resolution_stack[self._resolution_stack.index(cache_key):] + [cache_key]
            raise ExtendsCycleError(cycle=cycle)

        # Load section
        try:
            _, location = self._section_service.find_section(section_name, current_dir, scope_dir)
            section_cfg = self._section_service.load_section(location)
        except SectionNotFoundError as e:
            raise SectionNotFoundInExtendsError(
                section_name=section_name,
                parent_section=self._resolution_stack[-1] if self._resolution_stack else ""
            ) from e

        # Resolve with loaded config
        result = self.resolve_from_cfg(section_cfg, cache_key, scope_dir)

        return result

    def resolve_from_cfg(
        self,
        section_cfg: SectionCfg,
        section_name: str,
        scope_dir: Path,
        current_dir: str = ""
    ) -> ResolvedSectionData:
        """
        Resolve section from already loaded SectionCfg.

        Useful when section is already loaded (e.g., from template processing).

        Args:
            section_cfg: Loaded section configuration
            section_name: Section name for caching/cycle detection
            scope_dir: Current scope directory
            current_dir: Current directory for relative resolution of extends

        Returns:
            ResolvedSectionData with merged configuration
        """
        cache_key = section_name

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check for cycles
        if cache_key in self._resolution_stack:
            cycle = self._resolution_stack[self._resolution_stack.index(cache_key):] + [cache_key]
            raise ExtendsCycleError(cycle=cycle)

        # Push onto stack
        self._resolution_stack.append(cache_key)

        try:
            # Start with empty base
            base = self._create_empty_base()

            # Process extends in order (depth-first, left-to-right)
            for parent_ref in section_cfg.extends:
                parent_data = self._resolve_parent(parent_ref, scope_dir, current_dir)
                base = self._merge(base, parent_data)

            # Merge current section onto base
            current_data = self._extract_section_data(section_cfg)
            result = self._merge(base, current_data)

            # Preserve original config for filters/targets
            result.original_cfg = section_cfg

            # Cache result
            self._cache[cache_key] = result

            return result

        finally:
            # Pop from stack
            self._resolution_stack.pop()

    def resolve_from_resolved(self, resolved: ResolvedSection) -> ResolvedSectionData:
        """
        Resolve section from already resolved ResolvedSection.

        Type-safe public API that extracts all necessary fields
        from the resolved section, preventing scope mismatch bugs.

        Args:
            resolved: Fully resolved section with scope and config

        Returns:
            ResolvedSectionData with merged configuration
        """
        return self.resolve_from_cfg(
            section_cfg=resolved.section_config,
            section_name=resolved.canon_key(),
            scope_dir=resolved.scope_dir,
            current_dir=resolved.current_dir,
        )

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()

    def _build_cache_key(self, section_name: str, scope_dir: Path) -> str:
        """Build canonical cache key for a section."""
        # For addressed references, include the scope
        if section_name.startswith('@'):
            return section_name
        # For local references, include scope path
        return f"{scope_dir}:{section_name}"

    def _resolve_parent(self, parent_ref: str, scope_dir: Path, current_dir: str = "") -> ResolvedSectionData:
        """
        Resolve parent section from extends reference.

        Handles addressed references (@scope:name).

        Args:
            parent_ref: Reference to parent section (name or @scope:name)
            scope_dir: Current scope directory
            current_dir: Current directory for relative resolution
        """
        if parent_ref.startswith('@'):
            # Addressed reference: @scope:name or @[scope]:name
            return self._resolve_addressed(parent_ref, scope_dir)
        else:
            # Local reference - use current_dir for relative resolution
            return self.resolve(parent_ref, scope_dir, current_dir)

    def _resolve_addressed(self, ref: str, current_scope: Path) -> ResolvedSectionData:
        """
        Resolve addressed section reference.

        Formats:
        - @scope:name
        - @[scope]:name (for scopes with colons)
        - @/:name (root scope)
        """
        # Parse reference
        if ref.startswith('@['):
            # Bracketed form
            close = ref.find(']:')
            if close < 0:
                raise ValueError(f"Invalid bracketed reference: {ref}")
            scope = ref[2:close]
            name = ref[close + 2:]
        else:
            # Simple form @scope:name
            parts = ref[1:].split(':', 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid addressed reference: {ref}")
            scope, name = parts

        # Resolve scope directory
        if scope == '' or scope == '/':
            # Root scope - find repo root
            target_scope = self._find_repo_root(current_scope)
        else:
            # Relative scope
            target_scope = (current_scope / scope).resolve()

        return self.resolve(name, target_scope)

    def _find_repo_root(self, start: Path) -> Path:
        """Find repository root (directory containing lg-cfg at top level)."""
        current = start.resolve()
        while current != current.parent:
            if (current / "lg-cfg").is_dir():
                # Check if this is the root (no parent lg-cfg)
                parent_cfg = current.parent / "lg-cfg"
                if not parent_cfg.is_dir():
                    return current
            current = current.parent
        return start  # Fallback

    def _create_empty_base(self) -> ResolvedSectionData:
        """Create empty base for merging."""
        return ResolvedSectionData(
            adaptive_model=AdaptiveModel(),
            extensions=[],
            adapters={},
            skip_empty=True,
            path_labels="scope_relative",
            original_cfg=None,
        )

    def _extract_section_data(self, cfg: SectionCfg) -> ResolvedSectionData:
        """Extract ResolvedSectionData from SectionCfg."""
        return ResolvedSectionData(
            adaptive_model=extract_adaptive_model(cfg),
            extensions=list(cfg.extensions),
            adapters=dict(cfg.adapters),
            skip_empty=cfg.skip_empty,
            path_labels=cfg.path_labels,
            original_cfg=cfg,
        )

    def _merge(
        self,
        base: ResolvedSectionData,
        override: ResolvedSectionData
    ) -> ResolvedSectionData:
        """
        Merge two ResolvedSectionData, override wins on conflicts.

        Merge rules:
        - adaptive_model: use AdaptiveModel.merge_with()
        - extensions: union
        - adapters: deep merge, child wins
        - skip_empty, path_labels: child wins
        - original_cfg: NOT merged (set separately)
        """
        # Merge adaptive model
        merged_model = base.adaptive_model.merge_with(override.adaptive_model)

        # Union extensions
        merged_extensions = list(base.extensions)
        for ext in override.extensions:
            if ext not in merged_extensions:
                merged_extensions.append(ext)

        # Deep merge adapters
        merged_adapters = self._merge_adapters(base.adapters, override.adapters)

        return ResolvedSectionData(
            adaptive_model=merged_model,
            extensions=merged_extensions,
            adapters=merged_adapters,
            skip_empty=override.skip_empty,
            path_labels=override.path_labels,
            original_cfg=None,  # Set separately after all merges
        )

    def _merge_adapters(
        self,
        base: Dict[str, AdapterConfig],
        override: Dict[str, AdapterConfig]
    ) -> Dict[str, AdapterConfig]:
        """
        Deep merge adapter configurations.

        Child adapter configs override parent configs.
        Within an adapter, options are merged with child winning.
        """
        result = dict(base)

        for adapter_name, override_cfg in override.items():
            if adapter_name in result:
                # Merge adapter configs
                base_cfg = result[adapter_name]
                merged_cfg = self._merge_single_adapter(base_cfg, override_cfg)
                result[adapter_name] = merged_cfg
            else:
                result[adapter_name] = override_cfg

        return result

    def _merge_single_adapter(
        self,
        base: AdapterConfig,
        override: AdapterConfig
    ) -> AdapterConfig:
        """Merge two AdapterConfig objects."""
        # Merge base options
        merged_base = dict(base.base_options)
        merged_base.update(override.base_options)

        # Merge conditional options (child's conditionals added after parent's)
        merged_conditionals = list(base.conditional_options) + list(override.conditional_options)

        return AdapterConfig(
            base_options=merged_base,
            conditional_options=merged_conditionals,
        )


__all__ = ["ExtendsResolver", "ResolvedSectionData"]
