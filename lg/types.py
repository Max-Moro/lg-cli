from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, NewType, Mapping, Any, Set
from pathlib import Path


# ---- Aliases for clarity ----
PathLabelMode = Literal["scope_relative", "relative", "basename"]
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
    # Task context
    task_text: Optional[str] = None  # текст текущей задачи из --task
    # VCS context
    target_branch: Optional[str] = None  # целевая ветка для режима branch-changes


# ---- Спецификация цели ----

@dataclass(frozen=True)
class TargetSpec:
    """
    Спецификация цели обработки.

    Описывает что именно нужно обработать:
    контекст или отдельную секцию.
    """
    kind: Literal["context", "section"]
    name: str  # "docs/arch" или "all"

    # Для контекстов - путь к файлу шаблона
    template_path: Path


# ---- Секции и ссылки ----

@dataclass(frozen=True)
class SectionRef:
    """
    Ссылка на секцию с информацией о разрешении.
    """
    name: str  # Имя секции, используемое в шаблоне
    scope_rel: str  # Путь к директории области (относительно корня репозитория)
    scope_dir: Path  # Aбсолютный путь каталога-скоупа (cfg_root.parent)

    def canon_key(self) -> str:
        """
        Возвращает канонический ключ для этой секции.
        Используется для кэширования и дедупликации.
        """
        if self.scope_rel:
            return f"sec@{self.scope_rel}:{self.name}"
        else:
            return f"sec:{self.name}"


# ---- Файлы ----

@dataclass(frozen=True)
class FileEntry:
    """
    Представляет файл для включения в секцию.

    Содержит всю информацию, необходимую для обработки файла
    через языковые адаптеры.
    """
    abs_path: Path
    rel_path: str  # Относительно корня репозитория
    language_hint: LangName
    adapter_overrides: Dict[str, Dict] = field(default_factory=dict)
    size_bytes: int = 0  # Размер файла в байтах

    def __post_init__(self):
        """Вычисляет размер файла, если не указан."""
        if self.size_bytes == 0 and self.abs_path.exists():
            object.__setattr__(self, 'size_bytes', self.abs_path.stat().st_size)

# ---- Манифесты и планы ----

@dataclass
class SectionManifest:
    """
    Манифест одной секции со всеми её файлами.

    Содержит результат фильтрации файлов для конкретной секции
    с учетом активных тегов и режимов.
    """
    ref: SectionRef
    files: List[FileEntry]
    path_labels: PathLabelMode
    is_doc_only: bool  # True если секция содержит только markdown/plain text
    adapters_cfg: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class SectionPlan:
    """
    План для рендеринга одной секции.

    Содержит информацию о том, как отображать
    файлы в итоговом документе.
    """
    manifest: SectionManifest
    files: List[FileEntry]
    use_fence: bool  # Использовать ли fenced-блоки
    labels: Dict[str, str] = field(default_factory=dict)  # rel_path -> отображаемая метка


# ---- Обработанные файлы ----

@dataclass(frozen=True)
class ProcessedFile:
    """
    Обработанный файл, готовый для рендеринга.

    Содержит результат работы языкового адаптера.
    Статистические данные собираются отдельно через StatsCollector.
    """
    abs_path: Path
    rel_path: str
    processed_text: str
    meta: Dict[str, int | float | str | bool]
    raw_text: str
    cache_key: str


# ---- Отрендеренные секции ----

@dataclass(frozen=True)
class RenderBlock:
    """
    Блок отрендеренного содержимого.

    Представляет один fenced-блок или секцию без fence.
    """
    lang: LangName
    text: str  # уже с маркерами файлов / fenced
    file_paths: List[str]  # какие rel_paths попали в блок (для трассировки)

@dataclass
class RenderedSection:
    """
    Финальная отрендеренная секция.

    Содержит итоговый текст секции и список обработанных файлов.
    Статистика собирается отдельно через StatsCollector.
    """
    ref: SectionRef
    text: str
    files: List[ProcessedFile]
    blocks: List[RenderBlock] = field(default_factory=list)

# ---- Статистика (используется StatsCollector) ----

@dataclass
class FileStats:
    """
    Статистика по файлу для StatsCollector.
    """
    path: str
    size_bytes: int
    tokens_raw: int
    tokens_processed: int
    saved_tokens: int
    saved_pct: float
    meta: Dict[str, int | float | str | bool]
    sections: List[str] = field(default_factory=list)  # список секций где использован файл


@dataclass
class SectionStats:
    """
    Статистика по отрендеренной секции для StatsCollector.
    """
    ref: SectionRef
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
