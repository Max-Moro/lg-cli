"""
Path addressing system for LG templates.

Provides a unified API for parsing and resolving paths
from template placeholders.
"""

from .types import (
    ResourceConfig,
    ParsedPath,
    ResolvedPath,
    DirectoryContext,
    ResolvedResource,
    ResolvedFile,
    ResolvedSection,
    ResourceResolver,
)

from .parser import PathParser

from .resolver import PathResolver

from .context import AddressingContext

from .resolvers import FileResolver, SectionResolver

from .errors import (
    AddressingError,
    PathParseError,
    PathResolutionError,
    ScopeNotFoundError,
)


__all__ = [
    # Types
    "ResourceConfig",
    "ParsedPath",
    "ResolvedPath",
    "DirectoryContext",
    "ResolvedResource",
    "ResolvedFile",
    "ResolvedSection",
    "ResourceResolver",

    # Main classes
    "PathParser",
    "PathResolver",
    "AddressingContext",
    "FileResolver",
    "SectionResolver",

    # Exceptions
    "AddressingError",
    "PathParseError",
    "PathResolutionError",
    "ScopeNotFoundError",
]
