"""
Data types for the addressing system.

Defines core types for path parsing and resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from ..section import SectionLocation, SectionCfg


@dataclass(frozen=True)
class ResourceConfig:
    """
    Configuration for resolving a resource type.

    Defines how paths for this resource type should be parsed and resolved.
    Plugins define their own configs; addressing system uses them generically.
    """
    # Resource type identifier (tpl, ctx, md, sec) - used for canon_key and error messages
    kind: str

    # Extension handling: auto-add extension if not present (None = no extension)
    extension: Optional[str] = None

    # Path syntax: strip #anchor and ,params before resolving
    strip_md_syntax: bool = False

    # Resolution behavior: True = resolve relative to scope root (outside lg-cfg/)
    resolve_outside_cfg: bool = False

    # NEW: True = this is a section reference (uses SectionService)
    is_section: bool = False


@dataclass(frozen=True)
class ParsedPath:
    """
    Result of parsing a path string from a placeholder.

    Represents the "raw" path before resolution — as specified in template.
    Universal structure for all resource types (sections, templates, contexts, markdown).
    """
    config: ResourceConfig  # Resource configuration

    # Scope (origin)
    origin: Optional[str]       # None = implicit (from context), "self" = explicit current
    origin_explicit: bool       # True if @ was explicitly specified

    # Path to resource
    path: str                   # Path as specified (may be relative)
    is_absolute: bool           # True if starts with /


@dataclass
class DirectoryContext:
    """
    Current directory context for resolving relative paths.

    One element of the context stack.
    """
    origin: str                 # Scope ("self" or path like "apps/web")
    current_dir: str            # Current directory inside lg-cfg/ (POSIX, no leading /)
    cfg_root: Path              # Absolute path to lg-cfg/ of this scope

    def __repr__(self) -> str:
        return f"DirectoryContext(origin={self.origin!r}, current_dir={self.current_dir!r})"


@dataclass(frozen=True)
class ResolvedResource:
    """Base result of resolving any resource."""
    scope_dir: Path      # Absolute path to scope directory (parent of lg-cfg)
    scope_rel: str       # Relative path of scope from repo root

    def canon_key(self) -> str:
        """Returns canonical key for statistics and deduplication."""
        raise NotImplementedError("Subclasses must implement canon_key()")

    def _format_key(self, kind: str, resource_id: str) -> str:
        """Format key as 'kind:id' or 'kind@scope:id'."""
        if self.scope_rel:
            return f"{kind}@{self.scope_rel}:{resource_id}"
        return f"{kind}:{resource_id}"


@dataclass(frozen=True)
class ResolvedFile(ResolvedResource):
    """Result of resolving a file resource (tpl, ctx, md)."""
    cfg_root: Path       # Absolute path to lg-cfg/
    resource_path: Path  # Full path to file
    resource_rel: str    # Relative path inside lg-cfg/
    kind: str            # Resource type: "tpl", "ctx", "md"

    def canon_key(self) -> str:
        # Remove extension from resource_rel for cleaner keys
        resource_id = self.resource_rel
        if self.kind == "tpl" and resource_id.endswith(".tpl.md"):
            resource_id = resource_id[:-7]
        elif self.kind == "ctx" and resource_id.endswith(".ctx.md"):
            resource_id = resource_id[:-7]
        return self._format_key(self.kind, resource_id)


@dataclass(frozen=True)
class ResolvedSection(ResolvedResource):
    """
    Result of resolving a section.

    Contains all necessary information for processing section
    without repeated calls to SectionService.
    """
    location: SectionLocation       # Physical location of section
    section_config: SectionCfg      # Already loaded configuration
    name: str                       # Original reference from template (for error messages)
    canonical_name: str = ""        # Full name in scope index (e.g., "adapters/src")
    current_dir: str = ""           # Directory inside lg-cfg at resolution time (for extends)

    def canon_key(self) -> str:
        # _format_key uses scope_rel for cross-scope references automatically
        return self._format_key("sec", self.canonical_name)


@runtime_checkable
class ContextView(Protocol):
    """Read-only view of addressing context for resolvers."""

    @property
    def repo_root(self) -> Path: ...

    @property
    def cfg_root(self) -> Path: ...

    @property
    def current_directory(self) -> str: ...


@runtime_checkable
class ResourceResolver(Protocol):
    """Common interface for resolving any resources."""

    def resolve(
        self,
        name: str,
        config: ResourceConfig,
    ) -> ResolvedResource:
        """
        Resolve resource name to concrete location.

        Args:
            name: Resource name from template
            config: Resource configuration determining resolution behavior

        Returns:
            Resolved resource
        """
        ...


__all__ = [
    "ResourceConfig",
    "ParsedPath",
    "DirectoryContext",
    "ResolvedResource",
    "ResolvedFile",
    "ResolvedSection",
    "ContextView",
    "ResourceResolver",
]
