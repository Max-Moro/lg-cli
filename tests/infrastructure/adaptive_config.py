"""
Конфигурационные классы для адаптивных возможностей.

Предоставляет dataclasses для режимов и тегов, используемых в 
адаптивной системе Listing Generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ModeConfig:
    """Конфигурация одного режима."""
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class ModeSetConfig:
    """Конфигурация набора режимов."""
    title: str
    modes: Dict[str, ModeConfig]


@dataclass
class TagConfig:
    """Конфигурация одного тега.""" 
    title: str
    description: str = ""


@dataclass
class TagSetConfig:
    """Конфигурация набора тегов."""
    title: str
    tags: Dict[str, TagConfig]


__all__ = [
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig"
]