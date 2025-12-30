"""
Data types for the addressing system.

Defines core types for path parsing and resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class ResourceKind(Enum):
    """Type of resource being addressed."""
    SECTION = "section"
    TEMPLATE = "tpl"
    CONTEXT = "ctx"
    MARKDOWN = "md"              # md with @ (inside lg-cfg)
    MARKDOWN_EXTERNAL = "md_external"  # md without @ (outside lg-cfg, relative to current scope)


@dataclass(frozen=True)
class ParsedPath:
    """
    Result of parsing a path string from a placeholder.

    Represents the "raw" path before resolution — as specified in template.
    """
    kind: ResourceKind

    # Scope (origin)
    origin: Optional[str]       # None = implicit (from context), "self" = explicit current
    origin_explicit: bool       # True if @ was explicitly specified

    # Path to resource
    path: str                   # Path as specified (may be relative)
    is_absolute: bool           # True if starts with /

    # Additional parameters (for md)
    anchor: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedPath:
    """
    Fully resolved path to a resource.

    Result of resolution — ready for use in loading.
    """
    kind: ResourceKind

    # Resolved scope
    scope_dir: Path             # Absolute path to scope directory (parent of lg-cfg)
    scope_rel: str              # Relative path of scope from repo root

    # Resolved path inside lg-cfg
    cfg_root: Path              # Absolute path to lg-cfg/
    resource_path: Path         # Full path to file/resource
    resource_rel: str           # Relative path inside lg-cfg/

    # For sections — canonical ID
    canonical_id: Optional[str] = None

    # Original parameters (for md)
    anchor: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


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


__all__ = [
    "ResourceKind",
    "ParsedPath",
    "ResolvedPath",
    "DirectoryContext",
]
