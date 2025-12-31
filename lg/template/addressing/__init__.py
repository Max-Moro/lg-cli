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
)

from .parser import PathParser

from .resolver import PathResolver

from .context import AddressingContext

from .config_based_resolver import ConfigBasedResolver, ConfigProvider

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

    # Main classes
    "PathParser",
    "PathResolver",
    "AddressingContext",
    "ConfigBasedResolver",
    "ConfigProvider",

    # Exceptions
    "AddressingError",
    "PathParseError",
    "PathResolutionError",
    "ScopeNotFoundError",
]
