from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from lg.filters.model import FilterNode
SCHEMA_VERSION: int = 2


# ----------- секции адаптеров (пример: Python) ------------------ #
@dataclass
class LangPython:
    skip_empty: bool = True
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1


# ------------------------ корневой конфиг ----------------------- #
@dataclass
class Config:
    schema_version: int = SCHEMA_VERSION
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    exclude: List[str] = field(default_factory=list)        # deprecated
    skip_empty: bool = True                                 # глобальное правило
    python: LangPython = field(default_factory=LangPython)
