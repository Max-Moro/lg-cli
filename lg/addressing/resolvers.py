"""
Unified resolvers for addressing system.

Provides concrete implementations of ResourceResolver protocol
for different resource types.
"""

from __future__ import annotations

from pathlib import Path

from .context import AddressingContext
from .parser import PathParser
from .resolver import PathResolver
from .types import ResourceConfig, ResolvedFile, ResolvedSection
from ..section import SectionService


class FileResolver:
    """
    Resolver for file resources (templates, contexts, markdown).

    Wraps PathParser + PathResolver for unified interface.
    """

    def __init__(self, repo_root: Path):
        """
        Initialize file resolver.

        Args:
            repo_root: Repository root path
        """
        self._parser = PathParser()
        self._resolver = PathResolver(repo_root)
        self._repo_root = repo_root.resolve()

    def resolve(
        self,
        name: str,
        config: ResourceConfig,
        context: AddressingContext
    ) -> ResolvedFile:
        """
        Resolve file path.

        Args:
            name: File path from template (may include @origin:)
            config: Resource configuration (extension, etc.)
            context: Addressing context

        Returns:
            Resolved file path
        """
        parsed = self._parser.parse(name, config)
        resolved = self._resolver.resolve(parsed, context)

        return ResolvedFile(
            scope_dir=resolved.scope_dir,
            scope_rel=resolved.scope_rel,
            cfg_root=resolved.cfg_root,
            resource_path=resolved.resource_path,
            resource_rel=resolved.resource_rel,
        )


class SectionResolver:
    """
    Resolver for sections from YAML configuration.

    Uses SectionService for lookup and loading.
    """

    def __init__(self, section_service: SectionService, repo_root: Path):
        """
        Initialize section resolver.

        Args:
            section_service: Section service for lookup and loading
            repo_root: Repository root path
        """
        self._service = section_service
        self._repo_root = repo_root.resolve()

    def resolve(
        self,
        name: str,
        context: AddressingContext
    ) -> ResolvedSection:
        """
        Resolve section reference.

        Handles both simple references and addressed references (@origin:name).

        Args:
            name: Section reference from template
            context: Addressing context

        Returns:
            Resolved section with loaded configuration
        """
        # Check for addressed reference
        if name.startswith('@'):
            return self._resolve_addressed(name, context)

        # Simple reference - context-dependent search
        return self._resolve_simple(name, context)

    def _resolve_addressed(
        self,
        name: str,
        context: AddressingContext
    ) -> ResolvedSection:
        """
        Resolve addressed reference (@origin:name or @[origin]:name).
        """
        # Parse addressed reference
        origin, local_name = self._parse_addressed_ref(name)

        # Determine scope directory
        scope_dir, scope_rel = self._resolve_origin(origin, context)

        # Find section in target scope
        location = self._service.find_section(
            local_name,
            "",  # No current_dir for addressed refs
            scope_dir
        )

        # Load section configuration
        section_config = self._service.load_section(location)

        return ResolvedSection(
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            location=location,
            section_config=section_config,
            name=name,
        )

    def _resolve_simple(
        self,
        name: str,
        context: AddressingContext
    ) -> ResolvedSection:
        """
        Resolve simple reference with context-dependent search.
        """
        # Get current scope
        scope_dir = context.cfg_root.parent

        # Compute scope_rel
        try:
            scope_rel = scope_dir.relative_to(self._repo_root).as_posix()
            if scope_rel == ".":
                scope_rel = ""
        except ValueError:
            scope_rel = ""

        # Get current directory
        current_dir = context.current_directory

        # Find section using service
        location = self._service.find_section(name, current_dir, scope_dir)

        # Load section configuration
        section_config = self._service.load_section(location)

        return ResolvedSection(
            scope_dir=scope_dir,
            scope_rel=scope_rel,
            location=location,
            section_config=section_config,
            name=name,
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
        context: AddressingContext
    ) -> tuple[Path, str]:
        """
        Resolve origin to (scope_dir, scope_rel).

        Args:
            origin: Origin string from addressed reference
            context: Addressing context

        Returns:
            Tuple of (scope_dir, scope_rel)
        """
        if origin == '/' or origin == '':
            # Root scope
            return self._repo_root, ""

        # Relative to current scope
        current_scope = context.cfg_root.parent
        scope_dir = (current_scope / origin).resolve()
        return scope_dir, origin


__all__ = ["FileResolver", "SectionResolver"]
