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
    Markdown adapter configuration.
    """
    max_heading_level: int | None = None
    strip_h1: bool = False
    # drop block: sections/markers/frontmatter/placeholder policy
    drop: MarkdownDropCfg | None = None
    # keep block: sections to keep
    keep: MarkdownKeepCfg | None = None
    # enable conditional constructs processing in HTML comments
    enable_templating: bool = True
    # flag that placeholder is inside heading (affects H1 processing)
    placeholder_inside_heading: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        result = {}
        
        if self.max_heading_level is not None:
            result["max_heading_level"] = self.max_heading_level
        
        if self.strip_h1:
            result["strip_h1"] = self.strip_h1
        
        if self.drop is not None:
            result["drop"] = self.drop.to_dict()
        
        if self.keep is not None:
            result["keep"] = self.keep.to_dict()
        
        if not self.enable_templating:  # only if False (True - default)
            result["enable_templating"] = self.enable_templating

        if self.placeholder_inside_heading:  # only if True (False - default)
            result["placeholder_inside_heading"] = self.placeholder_inside_heading
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownCfg:
        if not d:
            # Config not provided → return default config
            return MarkdownCfg(
                max_heading_level=None,
                strip_h1=False,
                drop=None,
                keep=None,
                enable_templating=True,
                placeholder_inside_heading=False
            )
        _assert_only_keys(d, ["max_heading_level", "strip_h1", "drop", "keep", "enable_templating", "placeholder_inside_heading"], ctx="MarkdownCfg")
        max_heading_level = d.get("max_heading_level", None)
        strip_h1 = d.get("strip_h1", False)
        enable_templating = d.get("enable_templating", True)
        placeholder_inside_heading = d.get("placeholder_inside_heading", False)
        drop_cfg = d.get("drop", None)
        keep_cfg = d.get("keep", None)

        # Ensure mutual exclusion of drop and keep
        if drop_cfg and keep_cfg:
            raise ValueError("Cannot use both 'drop' and 'keep' modes simultaneously")

        # If drop block not provided — None.
        drop = MarkdownDropCfg.from_dict(drop_cfg) if drop_cfg is not None else None
        keep = MarkdownKeepCfg.from_dict(keep_cfg) if keep_cfg is not None else None
        
        return MarkdownCfg(
            max_heading_level=max_heading_level if max_heading_level is None else int(max_heading_level),
            strip_h1=strip_h1,
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
    flags: Optional[str] = None           # for regex: e.g. "i", "ms"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize section match rule to dictionary."""
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
    # One of the following must be set: match or path
    match: Optional[SectionMatch] = None
    path: Optional[List[str]] = None      # path of ancestors by exact names
    # Level restrictions
    level_exact: Optional[int] = None
    level_at_most: Optional[int] = None
    level_at_least: Optional[int] = None
    # Meta
    reason: Optional[str] = None
    placeholder: Optional[str] = None     # local placeholder template

    def to_dict(self) -> Dict[str, Any]:
        """Serialize section rule to dictionary."""
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
        # levels
        le = d.get("level_exact", None)
        leq = d.get("level_at_most", None)
        geq = d.get("level_at_least", None)
        # meta
        reason = d.get("reason")
        placeholder = d.get("placeholder")
        # invariant: at least one of match/path must be set
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
    template: Optional[str] = "> *(Omitted: {title}; −{lines} lines)*"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize placeholder policy to dictionary."""
        result = {}
        
        if self.mode != "none":
            result["mode"] = self.mode
        
        if self.template != "> *(Omitted: {title}; −{lines} lines)*":
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
        template = d.get("template", "> *(Omitted: {title}; −{lines} lines)*")
        if template is not None and not isinstance(template, str):
            raise TypeError("PlaceholderPolicy.template must be a string or null")
        return PlaceholderPolicy(mode=mode, template=template)

@dataclass
class MarkdownDropCfg:
    sections: List[SectionRule] = field(default_factory=list)
    frontmatter: bool = True # False = keep frontmatter
    placeholder: PlaceholderPolicy = field(default_factory=PlaceholderPolicy)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize drop configuration to dictionary."""
        result = {}

        if self.sections:
            result["sections"] = [section.to_dict() for section in self.sections]

        if not self.frontmatter:  # only if False (True - default)
            result["frontmatter"] = self.frontmatter
        
        placeholder_dict = self.placeholder.to_dict()
        if placeholder_dict:
            result["placeholder"] = placeholder_dict
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownDropCfg:
        """
        Parse drop block:
          - sections: list[SectionRule]
          - frontmatter: bool
          - placeholder: PlaceholderPolicy
        Accepts d=None → returns empty config.
        """
        if not d:
            # drop not provided → return empty config
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
        """Serialize keep configuration to dictionary."""
        result = {}

        if self.sections:
            result["sections"] = [section.to_dict() for section in self.sections]

        if self.frontmatter:  # only if True (False - default for keep)
            result["frontmatter"] = self.frontmatter
        
        return result

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> MarkdownKeepCfg:
        """
        Parse keep block:
          - sections: list[SectionRule]
          - frontmatter: bool
        Accepts d=None → returns empty config.
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
    """Heading node in document."""
    level: int                 # 1..6
    title: str                 # heading text (without '#', without setext underline)
    slug: str                  # github-style slug
    start_line: int            # heading line index (0-based)
    end_line_excl: int         # first line after this heading's subtree
    parents: List[int] = field(default_factory=list)  # parent indices by stack


@dataclass
class ParsedDoc:
    """
    Result of Markdown parsing:
      • source lines;
      • list of headings and their subtrees;
      • fenced block intervals (for info/debugging);
      • frontmatter interval (if present).
    """
    lines: List[str]
    headings: List[HeadingNode]
    fenced_ranges: List[Tuple[int, int]]        # [start, end_excl]
    frontmatter_range: Optional[Tuple[int, int]] = None

    def line_count(self) -> int:
        return len(self.lines)