from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Set, Optional


class VcsProvider(Protocol):
    def changed_files(self, root: Path) -> Set[str]:
        """
        Вернуть множество относительных POSIX-путей, которые считаются изменёнными:
        • staged + unstaged + untracked
        """
        ...
    
    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Вернуть множество относительных POSIX-путей, изменённых в текущей ветке
        относительно целевой ветки (или ближайшей родительской).
        """
        ...


@dataclass(frozen=True)
class NullVcs:
    """Fallback-провайдер, если git недоступен."""
    def changed_files(self, _root: Path) -> set[str]:
        return set()

    def branch_changed_files(self, _root: Path, _target_branch: Optional[str] = None) -> set[str]:
        return set()
