"""
Path addressing system for LG templates.

Provides a unified API for parsing and resolving paths
from template placeholders.
"""

from .types import (
    ResourceConfig,
    ParsedPath,
    DirectoryContext,
    ResolvedResource,
    ResolvedFile,
    ResolvedSection,
    ResourceResolver,
)

from .parser import PathParser

from .context import AddressingContext

from .file_resolver import FileResolver

from .section_resolver import SectionResolver

from .errors import (
    AddressingError,
    PathParseError,
    PathResolutionError,
    ScopeNotFoundError,
)

from .configs import SECTION_CONFIG


__all__ = [
    # Types
    "ResourceConfig",
    "ParsedPath",
    "DirectoryContext",
    "ResolvedResource",
    "ResolvedFile",
    "ResolvedSection",
    "ResourceResolver",

    # Main classes
    "PathParser",
    "AddressingContext",
    "FileResolver",
    "SectionResolver",

    # Configurations
    "SECTION_CONFIG",

    # Exceptions
    "AddressingError",
    "PathParseError",
    "PathResolutionError",
    "ScopeNotFoundError",
]
