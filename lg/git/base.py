"""
Base VCS abstractions.

Contains protocol and fallback implementation that are VCS-agnostic,
allowing future extension to other version control systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Set, Optional


class VcsProvider(Protocol):
    """
    Protocol for version control system providers.

    Defines the interface that any VCS implementation must follow.
    Currently implemented by GitVcs, but designed to support
    other VCS systems (Mercurial, SVN, etc.) in the future.
    """

    def changed_files(self, root: Path) -> Set[str]:
        """
        Return a set of relative POSIX paths that are considered changed.

        For Git this includes:
        - staged changes
        - unstaged changes
        - untracked files (not ignored)

        Args:
            root: Repository root directory

        Returns:
            Set of relative POSIX paths
        """
        ...

    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Return a set of relative POSIX paths changed in the current branch
        relative to the target branch (or nearest parent).

        Args:
            root: Repository root directory
            target_branch: Target branch for comparison (auto-detected if None)

        Returns:
            Set of relative POSIX paths changed in the branch
        """
        ...


@dataclass(frozen=True)
class NullVcs:
    """
    Fallback VCS provider when no VCS is available.

    Returns empty sets for all queries, effectively treating
    all files as unchanged.
    """

    def changed_files(self, _root: Path) -> Set[str]:
        """Return empty set (no changes detected)."""
        return set()

    def branch_changed_files(self, _root: Path, _target_branch: Optional[str] = None) -> Set[str]:
        """Return empty set (no branch changes detected)."""
        return set()


__all__ = [
    "VcsProvider",
    "NullVcs",
]
