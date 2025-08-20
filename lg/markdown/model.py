from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class MarkdownCfg:
    """
    Конфиг Markdown-адаптера (итерация 0–1).
    Пока только нормализация заголовков и фронтматтеровый флаг-заглушка (не используется).
    В следующих итерациях сюда добавим drop/sections/markers/placeholder.
    """
    max_heading_level: int | None = None
    # зарезервировано на будущее (drop/… добавим позже)
    frontmatter: bool | None = None


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
