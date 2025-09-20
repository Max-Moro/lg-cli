from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, NewType, Mapping, Any, Set

# ---- Aliases for clarity ----
PathLabelMode = Literal["auto", "relative", "basename", "off"]
LangName = NewType("LangName", str)  # "python" | "markdown" | "" ...
LANG_NONE: LangName = LangName("")
ModelName = NewType("ModelName", str)  # "o3", "gpt-4o", ...
RepoRelPath = NewType("RepoRelPath", str) # repo-root relative POSIX path
AdapterName = NewType("AdapterName", str)
AdapterRawCfg = Mapping[str, Any]

# -----------------------------
@dataclass(frozen=True)
class RunOptions:
    model: ModelName = ModelName("o3")
    # Адаптивные возможности
    modes: Dict[str, str] = field(default_factory=dict)  # modeset -> mode
    extra_tags: Set[str] = field(default_factory=set)  # дополнительные теги

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
