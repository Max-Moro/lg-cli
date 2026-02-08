"""
Section resolver for the addressing system.

Resolves section references to loaded section configurations.
"""

from __future__ import annotations

from pathlib import Path

from .errors import ScopeNotFoundError
from .types import ResolvedSection, ResourceResolver, ResourceConfig, ContextView
from ..section import SectionService


class SectionResolver(ResourceResolver):
    """
    Resolver for sections from YAML configuration.

    Uses SectionService for lookup and loading.
    """

    def __init__(self, section_service: SectionService, context: ContextView):
        """
        Initialize section resolver.

        Args:
            section_service: Section service for lookup and loading
            context: Addressing context
        """
        self._service = section_service
        self._context = context
        self._repo_root = context.repo_root

    def resolve(
        self,
        name: str,
        _config: ResourceConfig,
    ) -> ResolvedSection:
        """
        Resolve section reference.

        Handles both simple references and addressed references (@origin:name).

        Args:
            name: Section reference from template
            _config: Resource configuration (unused for sections, but required by protocol)

        Returns:
            Resolved section with loaded configuration
        """
        # Check for addressed reference
        if name.startswith('@'):
            return self._resolve_addressed(name)

        # Simple reference - context-dependent search
        return self._resolve_simple(name)

    def _resolve_addressed(
        self,
        name: str,
    ) -> ResolvedSection:
        """
        Resolve addressed reference (@origin:name or @[origin]:name).
        """
        # Parse addressed reference
        origin, local_name = self._parse_addressed_ref(name)

        # Determine scope directory
        scope_dir, scope_rel = self._resolve_origin(origin)

        # Find section in target scope
        try:
            canonical_name, location = self._service.find_section(
                local_name,
                "",  # No current_dir for addressed refs
                scope_dir
            )
        except RuntimeError as e:
            # Convert low-level "No lg-cfg/ directory found" to ScopeNotFoundError
            if "No lg-cfg/ directory found" in str(e):
                raise ScopeNotFoundError(
                    message=f"Scope not found: {origin}",
                    scope_path=origin
                )
            raise

        # Load section configuration
        section_config = self._service.load_section(location)

        return ResolvedSection(
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            location=location,
            section_config=section_config,
            name=name,
            canonical_name=canonical_name,
        )

    def _resolve_simple(
        self,
        name: str,
    ) -> ResolvedSection:
        """
        Resolve simple reference with context-dependent search.
        """
        # Get current scope
        scope_dir = self._context.cfg_root.parent

        # Compute scope_rel
        try:
            scope_rel = scope_dir.relative_to(self._repo_root).as_posix()
            if scope_rel == ".":
                scope_rel = ""
        except ValueError:
            scope_rel = ""

        # Get current directory (captured for extends resolution)
        current_dir = self._context.current_directory

        # Find section using service
        canonical_name, location = self._service.find_section(name, current_dir, scope_dir)

        # Load section configuration
        section_config = self._service.load_section(location)

        return ResolvedSection(
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            location=location,
            section_config=section_config,
            name=name,
            canonical_name=canonical_name,
            current_dir=current_dir,
        )

    def _parse_addressed_ref(self, name: str) -> tuple[str, str]:
        """
        Parse addressed reference into (origin, local_name).

        Formats:
        - @origin:name -> ("origin", "name")
        - @[origin]:name -> ("origin", "name")
        """
        if name.startswith('@['):
            # Bracket form: @[origin]:name
            close = name.find(']:')
            if close < 0:
                raise ValueError(f"Invalid bracketed addressed reference: {name}")
            origin = name[2:close]
            local_name = name[close + 2:]
        else:
            # Simple form: @origin:name
            if ':' not in name[1:]:
                raise ValueError(f"Invalid addressed reference (missing ':'): {name}")
            parts = name[1:].split(':', 1)
            origin = parts[0]
            local_name = parts[1]

        return origin, local_name

    def _resolve_origin(
        self,
        origin: str,
    ) -> tuple[Path, str]:
        """
        Resolve origin to (scope_dir, scope_rel).

        Args:
            origin: Origin string from addressed reference

        Returns:
            Tuple of (scope_dir, scope_rel)
        """
        if origin == '/' or origin == '':
            # Root scope
            return self._repo_root, ""

        # Relative to current scope
        current_scope = self._context.cfg_root.parent
        scope_dir = (current_scope / origin).resolve()
        return scope_dir, origin


__all__ = ["SectionResolver"]
