from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Set, Optional


class VcsProvider(Protocol):
    def changed_files(self, root: Path) -> Set[str]:
        """
        Return a set of relative POSIX paths that are considered changed:
        - staged + unstaged + untracked
        """
        ...

    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Return a set of relative POSIX paths changed in the current branch
        relative to the target branch (or nearest parent).
        """
        ...


@dataclass(frozen=True)
class NullVcs:
    """Fallback provider if git is unavailable."""
    def changed_files(self, _root: Path) -> set[str]:
        return set()

    def branch_changed_files(self, _root: Path, _target_branch: Optional[str] = None) -> set[str]:
        return set()
