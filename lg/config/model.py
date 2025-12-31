from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

# Import SectionCfg from new location for backward compatibility
from ..section.model import SectionCfg


@dataclass
class Config:
    sections: Dict[str, SectionCfg] = field(default_factory=dict)
