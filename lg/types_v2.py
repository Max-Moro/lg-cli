"""
Новая IR-модель для LG V2: более простая и ориентированная на однопроходную обработку.

Основные отличия от старой модели:
- Упрощенная структура без сложной каноничности
- Интеграция с системой адаптивных возможностей
- Ориентация на обработку по запросу
- Поддержка инкрементального сбора статистики
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Set

from .cache.fs_cache import Cache
from .config.adaptive_loader import AdaptiveConfigLoader
from .stats import TokenService
from .types import LangName, PathLabelMode, RunOptions
from .vcs import VcsProvider

# ---- Секции и ссылки ----

@dataclass(frozen=True)
class SectionRef:
    """
    Ссылка на секцию с информацией о разрешении.
    
    В отличие от старого CanonSectionId, этот класс содержит
    всю необходимую информацию для обработки секции.
    """
    name: str         # Имя секции, используемое в шаблоне
    scope_path: str   # Путь к директории области (относительно корня репозитория)
    cfg_path: Path    # Абсолютный путь к директории конфигурации
    
    def canon_key(self) -> str:
        """
        Возвращает канонический ключ для этой секции.
        Используется для кэширования и дедупликации.
        """
        scope = self.scope_path or "."
        return f"{scope}::{self.name}"


# ---- Файлы и группировка ----

@dataclass(frozen=True)
class FileEntry:
    """
    Представляет файл для включения в секцию.
    
    Содержит всю информацию, необходимую для обработки файла
    через языковые адаптеры.
    """
    abs_path: Path
    rel_path: str      # Относительно корня репозитория
    language_hint: LangName
    adapter_overrides: Dict[str, Dict] = field(default_factory=dict)
    size_bytes: int = 0  # Размер файла в байтах
    
    def __post_init__(self):
        """Вычисляет размер файла, если не указан."""
        if self.size_bytes == 0 and self.abs_path.exists():
            object.__setattr__(self, 'size_bytes', self.abs_path.stat().st_size)


@dataclass
class FileGroup:
    """
    Группа файлов с одинаковым языком.
    
    Используется для группировки файлов при рендеринге
    в fenced-блоки или без них.
    """
    lang: LangName
    entries: List[FileEntry]
    mixed: bool = False  # True если в группе смешанные языки


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
    adapters_cfg: Dict[str, Dict] = field(default_factory=dict)
    
    # Метаданные секции
    scope_dir: Path = field(default_factory=lambda: Path())
    scope_rel: str = ""


@dataclass
class SectionPlan:
    """
    План для рендеринга одной секции.
    
    Содержит информацию о том, как группировать и отображать
    файлы в итоговом документе.
    """
    manifest: SectionManifest
    groups: List[FileGroup]
    md_only: bool  # True если все файлы - markdown/plain text
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

# ---- Рендеринг документов ----

@dataclass(frozen=True)
class RenderBlock:
    """
    Блок отрендеренного содержимого.
    
    Представляет один fenced-блок или секцию без fence.
    """
    lang: LangName
    text: str                     # уже с маркерами файлов / fenced
    file_paths: List[str]         # какие rel_paths попали в блок (для трассировки)


@dataclass(frozen=True)
class RenderedDocument:
    """
    Полностью отрендеренный документ.
    
    Содержит итоговый текст и информацию о блоках
    для анализа и отладки.
    """
    text: str
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
    sections: Dict[str, int] = field(default_factory=dict)  # canon_key -> count


@dataclass
class SectionStats:
    """
    Статистика по отрендеренной секции для StatsCollector.
    """
    ref: SectionRef
    text: str
    tokens_processed: int
    tokens_raw: int
    total_size_bytes: int
    meta_summary: Dict[str, int] = field(default_factory=dict)


@dataclass
class TemplateStats:
    """
    Статистика по шаблону для StatsCollector.
    """
    key: str
    tokens: int
    text_size: int


# ---- Контекст выполнения ----

@dataclass
class ProcessingContext:
    """
    Контекст обработки для передачи состояния между компонентами.
    
    Содержит все необходимые сервисы и состояние
    для обработки шаблонов и секций.
    """
    # Базовые пути и настройки
    repo_root: Path
    cfg_root: Path
    options: RunOptions
    
    # Активное состояние адаптивных возможностей
    active_tags: Set[str]
    active_modes: Dict[str, str]
    
    # Сервисы (будут инициализированы извне)
    vcs: VcsProvider
    cache: Cache
    tokenizer: TokenService
    adaptive_loader: AdaptiveConfigLoader


# ---- Спецификация цели ----

@dataclass(frozen=True)
class TargetSpec:
    """
    Спецификация цели обработки.
    
    Описывает что именно нужно обработать:
    контекст или отдельную секцию.
    """
    kind: Literal["context", "section"]
    name: str                     # "docs/arch" или "all"
    
    # Для контекстов - путь к файлу шаблона
    template_path: Path

