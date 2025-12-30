"""
Specialized exceptions for the addressing system.

Provides informative error messages for path parsing and resolution failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .types import ParsedPath


class AddressingError(Exception):
    """Base class for addressing errors."""
    pass


@dataclass
class PathParseError(AddressingError):
    """Error parsing a path string."""
    message: str
    raw_path: str
    position: Optional[int] = None

    def __str__(self) -> str:
        if self.position is not None:
            return f"{self.message} at position {self.position}: {self.raw_path!r}"
        return f"{self.message}: {self.raw_path!r}"


@dataclass
class PathResolutionError(AddressingError):
    """Error resolving a path."""
    message: str
    parsed: Optional["ParsedPath"] = None
    searched_paths: List[str] = field(default_factory=list)
    hint: Optional[str] = None

    def __str__(self) -> str:
        parts = [self.message]

        if self.parsed:
            parts.append(f"  Path: {self.parsed.path}")
            if self.parsed.origin:
                parts.append(f"  Origin: {self.parsed.origin}")

        if self.searched_paths:
            parts.append("  Searched:")
            for p in self.searched_paths:
                parts.append(f"    - {p}")

        if self.hint:
            parts.append(f"  Hint: {self.hint}")

        return "\n".join(parts)


@dataclass
class ScopeNotFoundError(PathResolutionError):
    """Scope (lg-cfg/) not found."""
    scope_path: str = ""

    def __str__(self) -> str:
        return (
            f"Scope not found: {self.scope_path}\n"
            f"  Searched: {self.scope_path}/lg-cfg/\n"
            f"  Hint: Ensure the module has lg-cfg/ directory"
        )


__all__ = [
    "AddressingError",
    "PathParseError",
    "PathResolutionError",
    "ScopeNotFoundError",
]
