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
    strip_single_h1: bool = False
    # блок drop: секции/маркеры/frontmatter/политика плейсхолдеров
    drop: MarkdownDropCfg | None = None
    # блок keep: секции которые нужно оставить
    keep: MarkdownKeepCfg | None = None
    # включение обработки условных конструкций в HTML-комментариях
    enable_templating: bool = True
    # флаг что плейсхолдер находится внутри заголовка (влияет на обработку H1)
    placeholder_inside_heading: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует конфигурацию в словарь."""
        result = {}
        
        if self.max_heading_level is not None:
            result["max_heading_level"] = self.max_heading_level
        
        if self.strip_single_h1:
            result["strip_single_h1"] = self.strip_single_h1
        
        if self.drop is not None:
            result["drop"] = self.drop.to_dict()
        
        if self.keep is not None:
            result["keep"] = self.keep.to_dict()
        
        if not self.enable_templating:  # только если False (True - дефолт)
            result["enable_templating"] = self.enable_templating
        
        if self.placeholder_inside_heading:  # только если True (False - дефолт)
            result["placeholder_inside_heading"] = self.placeholder_inside_heading
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownCfg:
        if not d:
            # Конфиг не задан → возвращаем дефолтный конфиг
            return MarkdownCfg(
                max_heading_level=None,
                strip_single_h1=False,
                drop=None,
                keep=None,
                enable_templating=True,
                placeholder_inside_heading=False
            )
        _assert_only_keys(d, ["max_heading_level", "strip_single_h1", "drop", "keep", "enable_templating", "placeholder_inside_heading"], ctx="MarkdownCfg")
        max_heading_level = d.get("max_heading_level", None)
        strip_single_h1 = d.get("strip_single_h1", False)
        enable_templating = d.get("enable_templating", True)
        placeholder_inside_heading = d.get("placeholder_inside_heading", False)
        drop_cfg = d.get("drop", None)
        keep_cfg = d.get("keep", None)
        
        # Обеспечиваем взаимоисключение drop и keep
        if drop_cfg and keep_cfg:
            raise ValueError("Cannot use both 'drop' and 'keep' modes simultaneously")
            
        # Если блок drop не задан — None.
        drop = MarkdownDropCfg.from_dict(drop_cfg) if drop_cfg is not None else None
        keep = MarkdownKeepCfg.from_dict(keep_cfg) if keep_cfg is not None else None
        
        return MarkdownCfg(
            max_heading_level=max_heading_level if max_heading_level is None else int(max_heading_level),
            strip_single_h1=strip_single_h1,
            drop=drop,
            keep=keep,
            enable_templating=enable_templating,
            placeholder_inside_heading=placeholder_inside_heading,
        )

MatchKind = Literal["text", "slug", "regex"]

@dataclass
class SectionMatch:
    kind: MatchKind                       # "text" | "slug" | "regex"
    pattern: str
    flags: Optional[str] = None           # для regex: напр. "i", "ms"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует правило соответствия секций в словарь."""
        result = {
            "kind": self.kind,
            "pattern": self.pattern
        }
        
        if self.flags:
            result["flags"] = self.flags
        
        return result

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> SectionMatch:
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

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует правило секции в словарь."""
        result = {}
        
        if self.match:
            result["match"] = self.match.to_dict()
        
        if self.path:
            result["path"] = self.path
        
        if self.level_exact is not None:
            result["level_exact"] = self.level_exact
        
        if self.level_at_most is not None:
            result["level_at_most"] = self.level_at_most
        
        if self.level_at_least is not None:
            result["level_at_least"] = self.level_at_least
        
        if self.reason:
            result["reason"] = self.reason
        
        if self.placeholder:
            result["placeholder"] = self.placeholder
        
        return result

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> SectionRule:
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
class PlaceholderPolicy:
    mode: Literal["none", "summary"] = "none"
    template: Optional[str] = "> *(Опущено: {title}; −{lines} строк)*"

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует политику плейсхолдеров в словарь."""
        result = {}
        
        if self.mode != "none":
            result["mode"] = self.mode
        
        if self.template != "> *(Опущено: {title}; −{lines} строк)*":
            result["template"] = self.template
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> PlaceholderPolicy:
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
    frontmatter: bool = True # False = keep frontmatter
    placeholder: PlaceholderPolicy = field(default_factory=PlaceholderPolicy)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует конфигурацию drop в словарь."""
        result = {}
        
        if self.sections:
            result["sections"] = [section.to_dict() for section in self.sections]
        
        if not self.frontmatter:  # только если False (True - дефолт)
            result["frontmatter"] = self.frontmatter
        
        placeholder_dict = self.placeholder.to_dict()
        if placeholder_dict:
            result["placeholder"] = placeholder_dict
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownDropCfg:
        """
        Разбор блока drop:
          - sections: list[SectionRule]
          - frontmatter: bool
          - placeholder: PlaceholderPolicy
        Допускает d=None → вернётся пустой конфиг.
        """
        if not d:
            # drop не задан → возвращаем пустой конфиг
            return MarkdownDropCfg()
        _assert_only_keys(d, ["sections", "frontmatter", "placeholder"], ctx="MarkdownDropCfg")
        sections_raw = d.get("sections", []) or []
        if not isinstance(sections_raw, Iterable):
            raise TypeError("drop.sections must be a list")
        sections = [SectionRule.from_dict(x) for x in sections_raw]
        frontmatter = bool(d.get("frontmatter", True))
        placeholder = PlaceholderPolicy.from_dict(d.get("placeholder", None))
        return MarkdownDropCfg(
            sections=sections,
            frontmatter=frontmatter,
            placeholder=placeholder,
        )

@dataclass
class MarkdownKeepCfg:
    sections: List[SectionRule] = field(default_factory=list)
    frontmatter: bool = False  # True = keep frontmatter

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует конфигурацию keep в словарь."""
        result = {}
        
        if self.sections:
            result["sections"] = [section.to_dict() for section in self.sections]
        
        if self.frontmatter:  # только если True (False - дефолт для keep)
            result["frontmatter"] = self.frontmatter
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownKeepCfg:
        """
        Разбор блока keep:
          - sections: list[SectionRule]
          - frontmatter: bool
        Допускает d=None → вернётся пустой конфиг.
        """
        if not d:
            return MarkdownKeepCfg()
        _assert_only_keys(d, ["sections", "frontmatter"], ctx="MarkdownKeepCfg")
        sections_raw = d.get("sections", []) or []
        if not isinstance(sections_raw, Iterable):
            raise TypeError("keep.sections must be a list")
        sections = [SectionRule.from_dict(x) for x in sections_raw]
        frontmatter = bool(d.get("frontmatter", False))
        return MarkdownKeepCfg(
            sections=sections,
            frontmatter=frontmatter,
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