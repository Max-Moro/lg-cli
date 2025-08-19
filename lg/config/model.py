from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from lg.io.model import FilterNode
from ..adapters.markdown import MarkdownCfg
from ..adapters.python import PythonCfg

SCHEMA_VERSION = 6

@dataclass
class SectionCfg:
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    skip_empty: bool = True                                 # глобальное правило
    code_fence: bool = True                                 # оборачивать файлы в ```{lang}

    markdown: MarkdownCfg = field(default_factory=MarkdownCfg)
    python: PythonCfg = field(default_factory=PythonCfg)

@dataclass
class Config:
    schema_version: int = SCHEMA_VERSION
    sections: Dict[str, SectionCfg] = field(default_factory=dict)
