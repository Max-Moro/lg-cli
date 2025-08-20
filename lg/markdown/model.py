from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Literal


@dataclass
class MarkdownCfg:
    """
    Конфиг Markdown-адаптера.
    """
    max_heading_level: int | None = None
    # блок drop: секции/маркеры/frontmatter/политика плейсхолдеров
    drop: MarkdownDropCfg | None = None

MatchKind = Literal["text", "slug", "regex"]

@dataclass
class SectionMatch:
    kind: MatchKind                       # "text" | "slug" | "regex"
    pattern: str
    flags: Optional[str] = None           # для regex: напр. "i", "ms"

@dataclass
class SectionRule:
    # Один из вариантов должен быть задан: match или path
    match: Optional[SectionMatch] = None
    path: Optional[List[str]] = None      # путь предков по точным названиям
    # Ограничители уровней
    level_exact: Optional[int] = None
    level_at_most: Optional[int] = None
    level_at_least: Optional[int] = None
    # Мета
    reason: Optional[str] = None
    placeholder: Optional[str] = None     # локальный шаблон плейсхолдера

@dataclass
class MarkerRule:
    start: str
    end: str
    include_markers: bool = True
    reason: Optional[str] = None
    placeholder: Optional[str] = None

@dataclass
class PlaceholderPolicy:
    mode: Literal["none", "summary"] = "summary"
    template: Optional[str] = "> *(Опущено: {title}; −{lines} строк)*"

@dataclass
class MarkdownDropCfg:
    sections: List[SectionRule] = field(default_factory=list)
    markers: List[MarkerRule] = field(default_factory=list)
    frontmatter: bool = False
    placeholder: PlaceholderPolicy = field(default_factory=PlaceholderPolicy)

# ---------- Markdown Pipeline Intermediate Representation ----------

@dataclass
class HeadingNode:
    """Узел заголовка в документе."""
    level: int                 # 1..6
    title: str                 # текст заголовка (без '#', без подчеркивания setext)
    slug: str                  # github-style slug
    start_line: int            # индекс строки заголовка (0-based)
    end_line_excl: int         # первая строка после поддерева этого заголовка
    parents: List[int] = field(default_factory=list)  # индексы родителей по стеку


@dataclass
class ParsedDoc:
    """
    Результат парсинга Markdown:
      • исходные строки;
      • список заголовков и их поддеревьев;
      • интервалы fenced-блоков (для информации/отладки);
      • frontmatter-интервал (если есть).
    """
    lines: List[str]
    headings: List[HeadingNode]
    fenced_ranges: List[Tuple[int, int]]        # [start, end_excl]
    frontmatter_range: Optional[Tuple[int, int]] = None

    def line_count(self) -> int:
        return len(self.lines)