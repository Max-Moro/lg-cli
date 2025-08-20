from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

from lg.io.model import FilterNode

SCHEMA_VERSION = 6

@dataclass
class SectionCfg:
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    skip_empty: bool = True                  # глобальное правило
    code_fence: bool = True                  # оборачивать файлы в ```{lang}
    # Ленивые конфиги адаптеров: имя_адаптера → сырой dict из YAML
    adapters: Dict[str, dict] = field(default_factory=dict)

@dataclass
class Config:
    schema_version: int = SCHEMA_VERSION
    sections: Dict[str, SectionCfg] = field(default_factory=dict)

EmptyPolicy = Literal["inherit", "include", "exclude"]
