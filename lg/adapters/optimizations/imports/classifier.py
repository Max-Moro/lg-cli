"""
Import classification for determining external vs local imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class ImportClassifier(ABC):
    """Abstract base for import classification (external vs local)."""

    @abstractmethod
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a module is external (third-party) or local."""
        pass


__all__ = ["ImportClassifier"]
