from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, NewType, Mapping, Any

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
    mode: Literal["all", "changes"] = "all"
    model: ModelName = "o3"
    code_fence: bool = True  # override config if needed

# -------- Context --------
@dataclass(frozen=True)
class CanonSectionId:
    """
    Канонический ID секции: (scope_rel :: name)
    scope_rel — путь к каталогу пакета (cfg_root.parent) относительно репо-рута в POSIX.
    Для корня репо используем пустую строку "" (в as_key печатаем как ".").
    """
    scope_rel: str
    name: str

    def as_key(self) -> str:
        return f"{self.scope_rel or '.'}::{self.name}"

@dataclass(frozen=True)
class SectionRef:
    """
    Секция.
    multiplicity — сколько раз она встречается в контексте/шаблонах.
    """
    canon: CanonSectionId
    cfg_root: Path
    ph: str
    multiplicity: int = 1

@dataclass(frozen=True)
class ContextSpec:
    # унифицированный источник правды для пайплайна
    # либо ctx:<name>, либо sec:<name> (виртуальный контекст)
    kind: Literal["context", "section"]
    name: str                     # "docs/arch" или "all"
    section_refs: List[SectionRef] = field(default_factory=list) # список адресных секций
    # Карта "сырой плейсхолдер → канонический ключ секции", нужна компоновщику.
    ph2canon: Dict[str, str] = field(default_factory=dict)

# -------- Manifest / Files --------
@dataclass(frozen=True)
class ManifestFile:
    abs_path: Path
    rel_path: RepoRelPath           # POSIX, repo-root relative
    section_id: CanonSectionId      # принадлежность к секции
    multiplicity: int               # кратность из ContextSpec
    language_hint: LangName         # для fenced-блоков
    adapter_overrides: Dict[str, Dict] = field(default_factory=dict)

@dataclass(frozen=True)
class SectionMeta:
    code_fence: bool
    path_labels: PathLabelMode
    scope_dir: Path               # абсолютный путь каталога-скоупа (cfg_root.parent)
    scope_rel: RepoRelPath        # repo-root relative ("" для корня)

@dataclass(frozen=True)
class ManifestSection:
    id: CanonSectionId
    meta: SectionMeta
    adapters_cfg: Dict[str, Dict]
    files: List[ManifestFile] = field(default_factory=list)

@dataclass(frozen=True)
class Manifest:
    # детерминированный порядок секций
    order: List[CanonSectionId]
    sections: Dict[CanonSectionId, ManifestSection]

    def iter_sections(self):
        for sid in self.order:
            sec = self.sections.get(sid)
            if sec:
                yield sec

    def iter_files(self):
        for sec in self.iter_sections():
            for f in sec.files:
                yield f

# -------- Planning / Grouping --------
@dataclass(frozen=True)
class Group:
    lang: LangName
    entries: List[ManifestFile]
    mixed: bool

# -------- Section-scoped planning --------
@dataclass(frozen=True)
class SectionPlan:
    section: str
    groups: list[Group]
    md_only: bool
    use_fence: bool
    # Карта «rel_path → печатаемая метка» для маркеров FILE в этой секции
    labels: Dict[str, str] = field(default_factory=dict)
    # Базовые конфиги адаптеров для этой секции (из соответствующего lg-cfg/)
    adapters_cfg: Dict[str, Dict] = field(default_factory=dict)

@dataclass(frozen=True)
class ContextPlan:
    sections: List[SectionPlan]

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
