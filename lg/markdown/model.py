from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Literal, Any, Dict, Iterable


# --- helpers ---------------------------------------------------------------
def _assert_only_keys(d: Dict[str, Any] | None, allowed: Iterable[str], *, ctx: str) -> None:
    if d is None:
        return
    allowed_set = set(allowed)
    extra = set(d.keys()) - allowed_set
    if extra:
        raise ValueError(f"{ctx}: unknown key(s): {', '.join(sorted(extra))}")

@dataclass
class MarkdownCfg:
    """
    Конфиг Markdown-адаптера.
    """
    max_heading_level: int | None = None
    # блок drop: секции/маркеры/frontmatter/политика плейсхолдеров
    drop: MarkdownDropCfg | None = None

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "MarkdownCfg":
        if not d:
            # Конфиг не задан → включаем дефолтные маркеры lg:omit
            return MarkdownCfg(
                max_heading_level=None,
                drop=MarkdownDropCfg._with_default_markers()
            )
        _assert_only_keys(d, ["max_heading_level", "drop"], ctx="MarkdownCfg")
        max_heading_level = d.get("max_heading_level", None)
        drop_cfg = d.get("drop", None)
        # Если блок drop не задан — создаём с дефолтными маркерами.
        drop = MarkdownDropCfg.from_dict(drop_cfg) if drop_cfg is not None else MarkdownDropCfg._with_default_markers()
        return MarkdownCfg(
            max_heading_level=max_heading_level if max_heading_level is None else int(max_heading_level),
            drop=drop,
        )

MatchKind = Literal["text", "slug", "regex"]

@dataclass
class SectionMatch:
    kind: MatchKind                       # "text" | "slug" | "regex"
    pattern: str
    flags: Optional[str] = None           # для regex: напр. "i", "ms"

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SectionMatch":
        if not isinstance(d, dict):
            raise TypeError("SectionMatch must be a mapping with keys: kind, pattern[, flags]")
        _assert_only_keys(d, ["kind", "pattern", "flags"], ctx="SectionMatch")
        kind = d.get("kind")
        pattern = d.get("pattern")
        flags = d.get("flags")
        if kind not in ("text", "slug", "regex"):
            raise ValueError(f"SectionMatch.kind must be one of 'text'|'slug'|'regex', got: {kind!r}")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("SectionMatch.pattern must be a non-empty string")
        if flags is not None and not isinstance(flags, str):
            raise TypeError("SectionMatch.flags must be a string if provided")
        return SectionMatch(kind=kind, pattern=pattern, flags=flags)

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

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SectionRule":
        if not isinstance(d, dict):
            raise TypeError("SectionRule must be a mapping")
        _assert_only_keys(
            d,
            [
                "match", "path",
                "level_exact", "level_at_most", "level_at_least",
                "reason", "placeholder",
            ],
            ctx="SectionRule",
        )
        match_raw = d.get("match")
        path_raw = d.get("path")
        match = SectionMatch.from_dict(match_raw) if match_raw is not None else None
        path: Optional[List[str]] = None
        if path_raw is not None:
            if isinstance(path_raw, (list, tuple)) and all(isinstance(x, str) for x in path_raw):
                path = list(path_raw)
            else:
                raise TypeError("SectionRule.path must be a list of strings")
        # уровни
        le = d.get("level_exact", None)
        leq = d.get("level_at_most", None)
        geq = d.get("level_at_least", None)
        # meta
        reason = d.get("reason")
        placeholder = d.get("placeholder")
        # инвариант: хотя бы одно из match/path должно быть задано
        if match is None and path is None:
            raise ValueError("SectionRule requires either 'match' or 'path'")
        return SectionRule(
            match=match,
            path=path,
            level_exact=int(le) if le is not None else None,
            level_at_most=int(leq) if leq is not None else None,
            level_at_least=int(geq) if geq is not None else None,
            reason=str(reason) if isinstance(reason, str) else (None if reason is None else str(reason)),
            placeholder=str(placeholder) if isinstance(placeholder, str) else (None if placeholder is None else str(placeholder)),
        )

@dataclass
class MarkerRule:
    start: str
    end: str
    include_markers: bool = True
    reason: Optional[str] = None
    placeholder: Optional[str] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MarkerRule":
        if not isinstance(d, dict):
            raise TypeError("MarkerRule must be a mapping")
        _assert_only_keys(d, ["start", "end", "include_markers", "reason", "placeholder"], ctx="MarkerRule")
        start = d.get("start")
        end = d.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError("MarkerRule requires 'start' and 'end' strings")
        include_markers = bool(d.get("include_markers", True))
        reason = d.get("reason")
        placeholder = d.get("placeholder")
        return MarkerRule(
            start=start,
            end=end,
            include_markers=include_markers,
            reason=str(reason) if isinstance(reason, str) else (None if reason is None else str(reason)),
            placeholder=str(placeholder) if isinstance(placeholder, str) else (None if placeholder is None else str(placeholder)),
        )

@dataclass
class PlaceholderPolicy:
    mode: Literal["none", "summary"] = "none"
    template: Optional[str] = "> *(Опущено: {title}; −{lines} строк)*"

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "PlaceholderPolicy":
        if not d:
            return PlaceholderPolicy(mode="none")
        _assert_only_keys(d, ["mode", "template"], ctx="PlaceholderPolicy")
        mode = d.get("mode", "none")
        if mode not in ("none", "summary"):
            raise ValueError("PlaceholderPolicy.mode must be 'none' or 'summary'")
        template = d.get("template", "> *(Опущено: {title}; −{lines} строк)*")
        if template is not None and not isinstance(template, str):
            raise TypeError("PlaceholderPolicy.template must be a string or null")
        return PlaceholderPolicy(mode=mode, template=template)

@dataclass
class MarkdownDropCfg:
    sections: List[SectionRule] = field(default_factory=list)
    markers: List[MarkerRule] = field(default_factory=list)
    frontmatter: bool = False
    placeholder: PlaceholderPolicy = field(default_factory=PlaceholderPolicy)

    @staticmethod
    def _default_omit_markers() -> List[MarkerRule]:
        """Стандартные маркеры lg:omit, включаемые по умолчанию."""
        return [MarkerRule(
            start="<!-- lg:omit:start -->",
            end="<!-- lg:omit:end -->",
            include_markers=True,
            reason="lg:omit default"
        )]

    @classmethod
    def _with_default_markers(cls) -> "MarkdownDropCfg":
        """Готовый drop-конфиг с дефолтными lg:omit-маркерами и placeholder=none."""
        return cls(
            sections=[],
            markers=cls._default_omit_markers(),
            frontmatter=False,
            placeholder=PlaceholderPolicy(mode="none")
        )

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "MarkdownDropCfg":
        """
        Разбор блока drop:
          - sections: list[SectionRule]
          - markers: list[MarkerRule]
          - frontmatter: bool
          - placeholder: PlaceholderPolicy
        Допускает d=None → вернётся конфиг по умолчанию (без правил).
        """
        if not d:
            # drop не задан → возвращаем конфиг с дефолтными lg:omit маркерами
            return MarkdownDropCfg._with_default_markers()
        _assert_only_keys(d, ["sections", "markers", "frontmatter", "placeholder"], ctx="MarkdownDropCfg")
        sections_raw = d.get("sections", []) or []
        # ВАЖНО: различаем «ключ отсутствует» и «пустой список».
        markers_key_present = ("markers" in d)
        markers_raw = d.get("markers", None)
        if markers_raw is None and not markers_key_present:
            # ключ не указан → подставляем дефолтные lg:omit-маркеры
            markers = MarkdownDropCfg._default_omit_markers()
        else:
            markers_raw = markers_raw or []
            markers = [MarkerRule.from_dict(x) for x in markers_raw]
        if not isinstance(sections_raw, Iterable):
            raise TypeError("drop.sections must be a list")
        sections = [SectionRule.from_dict(x) for x in sections_raw]
        frontmatter = bool(d.get("frontmatter", False))
        placeholder = PlaceholderPolicy.from_dict(d.get("placeholder", None))
        return MarkdownDropCfg(
            sections=sections,
            markers=markers,
            frontmatter=frontmatter,
            placeholder=placeholder,
        )

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