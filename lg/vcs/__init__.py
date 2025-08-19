from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Set


class VcsProvider(Protocol):
    def changed_files(self, root: Path) -> Set[str]:
        """
        Вернуть множество относительных POSIX-путей, которые считаются изменёнными:
        • staged + unstaged + untracked
        """
        ...


@dataclass(frozen=True)
class NullVcs:
    """Fallback-провайдер, если git недоступен."""
    def changed_files(self, root: Path) -> set[str]:
        return set()
