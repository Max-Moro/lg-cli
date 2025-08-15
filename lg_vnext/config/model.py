from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

SCHEMA_VERSION = 6

@dataclass
class MarkdownCfg:
    max_heading_level: Optional[int] = None

@dataclass
class PythonCfg:
    skip_empty: bool = True
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1

@dataclass
class SectionCfg:
    # Минимальный набор для этого шага. Далее добавим filters и прочее.
    extensions: List[str] = field(default_factory=lambda: [".py"])
    skip_empty: bool = True                                 # глобальное правило
    code_fence: bool = True                                 # оборачивать файлы в ```{lang}

    markdown: MarkdownCfg = field(default_factory=MarkdownCfg)
    python: PythonCfg = field(default_factory=PythonCfg)

@dataclass
class ConfigV6:
    schema_version: int = SCHEMA_VERSION
    sections: Dict[str, SectionCfg] = field(default_factory=dict)
