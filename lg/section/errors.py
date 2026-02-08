from __future__ import annotations

from typing import List

from ..errors import LGUserError


class SectionNotFoundError(LGUserError):
    """Raised when a section cannot be found."""
    def __init__(self, name: str, searched: List[str]):
        self.name = name
        self.searched = searched
        super().__init__(
            f"Section '{name}' not found. Searched: {', '.join(searched)}"
        )
