from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional

LangName = str  # "python" | "markdown" | "" ...
ModelName = str  # "o3", "gpt-4o", ...

# ----- Config Model Early -----
# Политика пустых файлов
EmptyPolicy = Literal["inherit", "include", "exclude"]

# -----------------------------
@dataclass(frozen=True)
class RunOptions:
    mode: Literal["all", "changes"] = "all"
    model: ModelName = "o3"
    code_fence: bool = True  # override config if needed

@dataclass(frozen=True)
class SectionUsage:
    by_name: Dict[str, int]  # {"core-model-src": 1, "docs": 2}

# -------- Context --------
@dataclass(frozen=True)
class ContextSpec:
    # унифицированный источник правды для пайплайна
    # либо ctx:<name>, либо sec:<name> (виртуальный контекст)
    kind: Literal["context", "section"]
    name: str                     # "docs/arch" или "all"
    sections: SectionUsage        # итоговый usage с кратностями

# -------- Manifest / Files --------
@dataclass(frozen=True)
class FileRef:
    abs_path: Path
    rel_path: str                 # POSIX
    section: str                  # секция, где был обнаружен файл
    multiplicity: int             # кратность из ContextSpec.sections
    language_hint: LangName       # для fenced-блоков

@dataclass(frozen=True)
class Manifest:
    files: List[FileRef]

# -------- Planning / Grouping --------
@dataclass(frozen=True)
class Group:
    lang: LangName
    entries: List[FileRef]
    mixed: bool

@dataclass(frozen=True)
class Plan:
    md_only: bool
    use_fence: bool
    groups: List[Group]           # стабильный порядок

# -------- Processed blobs --------
@dataclass(frozen=True)
class ProcessedBlob:
    abs_path: Path
    rel_path: str
    size_bytes: int
    processed_text: str
    meta: Dict[str, int | float | str | bool]
    raw_text: str
    cache_key_processed: str      # ключ processed-кэша
    cache_key_raw: str            # ключ raw-токенов

# -------- Rendering --------
@dataclass(frozen=True)
class RenderBlock:
    lang: LangName
    text: str                     # уже с маркерами файлов / fenced
    file_paths: List[str]         # какие rel_paths попали в блок (для трассировки)

@dataclass(frozen=True)
class RenderedDocument:
    text: str
    blocks: List[RenderBlock]     # полезно для отладки/GUI

# -------- Stats / Result --------
@dataclass(frozen=True)
class FileRow:
    path: str
    sizeBytes: int
    tokensRaw: int
    tokensProcessed: int
    savedTokens: int
    savedPct: float
    promptShare: float
    ctxShare: float
    meta: Dict[str, int | float | str | bool]

@dataclass(frozen=True)
class Totals:
    sizeBytes: int
    tokensProcessed: int
    tokensRaw: int
    savedTokens: int
    savedPct: float
    ctxShare: float
    renderedTokens: Optional[int] = None
    renderedOverheadTokens: Optional[int] = None
    metaSummary: Dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class ContextBlock:
    templateName: str
    sectionsUsed: Dict[str, int]
    finalRenderedTokens: Optional[int] = None
    templateOnlyTokens: Optional[int] = None
    templateOverheadPct: Optional[float] = None
    finalCtxShare: Optional[float] = None
