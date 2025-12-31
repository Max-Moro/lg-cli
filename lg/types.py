from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, NewType, Mapping, Set
from pathlib import Path

from .addressing.types import ResolvedSection


# ---- Aliases for clarity ----
PathLabelMode = Literal["scope_relative", "relative", "basename"]
LangName = NewType("LangName", str)  # "python" | "markdown" | "" ...
LANG_NONE: LangName = LangName("")
ModelName = NewType("ModelName", str)  # "o3", "gpt-4o", ...
RepoRelPath = NewType("RepoRelPath", str) # repo-root relative POSIX path
AdapterName = NewType("AdapterName", str)
AdapterRawCfg = Mapping[str, object]

# -----------------------------
@dataclass(frozen=True)
class RunOptions:
    # Tokenization parameters
    tokenizer_lib: str = "tiktoken"
    encoder: str = "cl100k_base"
    ctx_limit: int = 128000
    # Adaptive capabilities
    modes: Dict[str, str] = field(default_factory=dict)  # modeset -> mode
    extra_tags: Set[str] = field(default_factory=set)  # additional tags
    # Task context
    task_text: Optional[str] = None  # current task text from --task
    # VCS context
    target_branch: Optional[str] = None  # target branch for branch-changes mode


# ---- Target specification ----

@dataclass(frozen=True)
class TargetSpec:
    """
    Processing target specification.

    Describes what exactly needs to be processed:
    context or individual section.
    """
    kind: Literal["context", "section"]
    name: str  # "docs/arch" or "all"

    # For contexts - path to template file
    template_path: Path


# ---- Sections and references ----
# SectionRef has been replaced with ResolvedSection from addressing.types


# ---- Files ----

@dataclass(frozen=True)
class FileEntry:
    """
    Represents file for inclusion in section.

    Contains all information necessary for processing file
    through language adapters.
    """
    abs_path: Path
    rel_path: str  # Relative to repository root
    language_hint: LangName
    adapter_overrides: Dict[str, Dict] = field(default_factory=dict)
    size_bytes: int = 0  # File size in bytes

    def __post_init__(self):
        """Calculate file size if not specified."""
        if self.size_bytes == 0 and self.abs_path.exists():
            object.__setattr__(self, 'size_bytes', self.abs_path.stat().st_size)

# ---- Manifests and plans ----

@dataclass
class SectionManifest:
    """
    Manifest of a single section with all its files.

    Contains result of file filtering for specific section
    considering active tags and modes.
    """
    resolved: ResolvedSection
    files: List[FileEntry]
    path_labels: PathLabelMode
    is_doc_only: bool  # True if section contains only markdown/plain text
    is_local_files: bool = False
    adapters_cfg: Dict[str, dict] = field(default_factory=dict)


@dataclass
class SectionPlan:
    """
    Plan for rendering a single section.

    Contains information about how to display
    files in final document.
    """
    manifest: SectionManifest
    files: List[FileEntry]
    use_fence: bool  # Whether to use fenced blocks
    labels: Dict[str, str] = field(default_factory=dict)  # rel_path -> display label


# ---- Processed files ----

@dataclass(frozen=True)
class ProcessedFile:
    """
    Processed file ready for rendering.

    Contains result of language adapter work.
    Statistical data is collected separately through StatsCollector.
    """
    abs_path: Path
    rel_path: str
    processed_text: str
    meta: Dict[str, int | float | str | bool]  # type: ignore
    raw_text: str
    cache_key: str


# ---- Rendered sections ----

@dataclass(frozen=True)
class RenderBlock:
    """
    Block of rendered content.

    Represents one fenced block or section without fence.
    """
    lang: LangName
    text: str  # already with file markers / fenced
    file_paths: List[str]  # which rel_paths are in the block (for tracing)

@dataclass
class RenderedSection:
    """
    Final rendered section.

    Contains final section text and list of processed files.
    Statistics are collected separately through StatsCollector.
    """
    resolved: ResolvedSection
    text: str
    files: List[ProcessedFile]
    blocks: List[RenderBlock] = field(default_factory=list)

# ---- Statistics (used by StatsCollector) ----

@dataclass
class FileStats:
    """
    File statistics for StatsCollector.
    """
    path: str
    size_bytes: int
    tokens_raw: int
    tokens_processed: int
    saved_tokens: int
    saved_pct: float
    meta: Dict[str, int | float | str | bool]  # type: ignore
    sections: List[str] = field(default_factory=list)  # list of sections where file is used


@dataclass
class SectionStats:
    """
    Rendered section statistics for StatsCollector.
    """
    resolved: ResolvedSection
    text: str
    tokens_rendered: int
    total_size_bytes: int
    meta_summary: Dict[str, int] = field(default_factory=dict)

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
    meta: Dict[str, int | float | str | bool]  # type: ignore

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
    metaSummary: Dict[str, int] = field(default_factory=dict)  # type: ignore

@dataclass(frozen=True)
class ContextBlock:
    templateName: str
    sectionsUsed: Dict[str, int]
    finalRenderedTokens: Optional[int] = None
    templateOnlyTokens: Optional[int] = None
    templateOverheadPct: Optional[float] = None
    finalCtxShare: Optional[float] = None
