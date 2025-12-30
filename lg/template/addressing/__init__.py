"""
Path addressing system for LG templates.

Provides a unified API for parsing and resolving paths
from template placeholders.
"""

from .types import (
    ResourceKind,
    ParsedPath,
    ResolvedPath,
    DirectoryContext,
)

from .parser import PathParser

from .resolver import PathResolver

from .context import AddressingContext

from .errors import (
    AddressingError,
    PathParseError,
    PathResolutionError,
    ScopeNotFoundError,
)


__all__ = [
    # Types
    "ResourceKind",
    "ParsedPath",
    "ResolvedPath",
    "DirectoryContext",

    # Main classes
    "PathParser",
    "PathResolver",
    "AddressingContext",

    # Exceptions
    "AddressingError",
    "PathParseError",
    "PathResolutionError",
    "ScopeNotFoundError",
]
