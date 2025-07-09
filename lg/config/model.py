from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..adapters.markdown import LangMarkdown
from ..adapters.python import LangPython
from ..filters.model import FilterNode

SCHEMA_VERSION: int = 4


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
    code_fence: bool = False                                # оборачивать файлы в ```{lang}
    python: LangPython = field(default_factory=LangPython)
    markdown: LangMarkdown = field(default_factory=LangMarkdown)
