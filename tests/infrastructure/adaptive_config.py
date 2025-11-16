"""
Configuration classes for adaptive capabilities.

Provides dataclasses for modes and tags used in
the Listing Generator adaptive system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ModeConfig:
    """Configuration for a single mode."""
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModeSetConfig:
    """Configuration for a set of modes."""
    title: str
    modes: Dict[str, ModeConfig]


@dataclass
class TagConfig:
    """Configuration for a single tag."""
    title: str
    description: str = ""


@dataclass
class TagSetConfig:
    """Configuration for a set of tags."""
    title: str
    tags: Dict[str, TagConfig]


__all__ = [
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig"
]