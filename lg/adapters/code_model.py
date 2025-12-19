"""
Configuration model for language programming adapters.
Unified base configuration + language-specific extensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Union, Any

# ---- Types for configuration ----

VisibilityLevel = Literal["public", "protected", "private", "internal", "exported"]
FunctionBodyPolicy = Literal["keep_all", "strip_all", "keep_public"]
CommentPolicy = Literal["keep_all", "strip_all", "keep_doc", "keep_first_sentence"]
ImportPolicy = Literal["keep_all", "strip_all", "strip_external", "strip_local"]
PlaceholderStyle = Literal["inline", "block", "none"]


@dataclass
class FunctionBodyConfig:
    """Configuration for function/method body removal."""
    policy: FunctionBodyPolicy = "keep_all"
    max_tokens: Optional[int] = None  # trim body to fit token budget
    except_patterns: List[str] = field(default_factory=list)  # regex for exception function names
    keep_annotated: List[str] = field(default_factory=list)  # regex for decorator/annotation preservation


@dataclass
class CommentConfig:
    """Configuration for comment and documentation processing."""
    policy: CommentPolicy = "keep_all"
    max_tokens: Optional[int] = None  # maximum number of tokens for preserved comment
    keep_annotations: List[str] = field(default_factory=list)  # regex annotations for preservation
    strip_patterns: List[str] = field(default_factory=list)  # regex patterns for removal


@dataclass
class ImportConfig:
    """Configuration for import processing."""
    policy: ImportPolicy = "keep_all"
    summarize_long: bool = False  # enable summarization of long import lists
    max_items_before_summary: int = 10  # number of imports after which summarization is enabled
    external_patterns: List[str] = field(default_factory=list)  # regex for identifying external packages

@dataclass
class LiteralConfig:
    """Configuration for literal processing."""
    max_tokens: Optional[int] = None  # maximum allowed size of literal content in tokens


@dataclass
class BudgetConfig:
    """Token budgeting per file."""
    max_tokens_per_file: Optional[int] = None
    priority_order: List[str] = field(default_factory=list)


@dataclass
class PlaceholderConfig:
    """Configuration for placeholders of removed code."""
    style: PlaceholderStyle = "inline"
    # Token savings threshold: savings / placeholder >= min_savings_ratio
    min_savings_ratio: float = 2.0
    # Absolute savings threshold for style=="none" (complete removal).
    min_abs_savings_if_none: int = 5


@dataclass
class CodeCfg:
    """
    Base configuration for all language programming adapters.
    Inherited by language-specific configurations.
    """
    # Main policies
    public_api_only: bool = False
    strip_function_bodies: Union[bool, FunctionBodyConfig] = False
    comment_policy: Union[CommentPolicy, CommentConfig] = "keep_all"

    # Additional optimizations
    imports: ImportConfig = field(default_factory=ImportConfig)
    literals: LiteralConfig = field(default_factory=LiteralConfig)

    # Placeholder system
    placeholders: PlaceholderConfig = field(default_factory=PlaceholderConfig)

    # Budgeting
    budget: Optional[BudgetConfig] = None

    def general_load(self, d: Optional[Dict[str, Any]]):
        """Load universal part of configuration from YAML dictionary."""
        d = d or {}

        # Parse main fields
        self.public_api_only = bool(d.get("public_api_only", False))

        # strip_function_bodies: bool | dict
        sfb = d.get("strip_function_bodies", False)
        if isinstance(sfb, bool):
            self.strip_function_bodies = sfb
        elif isinstance(sfb, dict):
            self.strip_function_bodies = FunctionBodyConfig(
                policy=sfb.get("policy", "keep_all"),
                max_tokens=sfb.get("max_tokens"),
                except_patterns=list(sfb.get("except_patterns", [])),
                keep_annotated=list(sfb.get("keep_annotated", []))
            )

        # comment_policy: str | dict
        cp = d.get("comment_policy", "keep_all")
        if isinstance(cp, str):
            # Assign as CommentPolicy literal
            self.comment_policy = cp  # type: ignore[assignment]
        elif isinstance(cp, dict):
            self.comment_policy = CommentConfig(
                policy=cp.get("policy", "keep_all"),
                max_tokens=cp.get("max_tokens"),
                keep_annotations=list(cp.get("keep_annotations", [])),
                strip_patterns=list(cp.get("strip_patterns", []))
            )

        # Nested configs
        if "imports" in d:
            ic = d["imports"]
            self.imports = ImportConfig(
                policy=ic.get("policy", "keep_all"),
                summarize_long=bool(ic.get("summarize_long", False)),
                max_items_before_summary=int(ic.get("max_items_before_summary", 10)),
                external_patterns=list(ic.get("external_only_patterns", []))
            )

        if "literals" in d:
            lc = d["literals"]
            self.literals = LiteralConfig(
                max_tokens=lc.get("max_tokens")
            )

        if "placeholders" in d:
            pc = d["placeholders"]
            self.placeholders = PlaceholderConfig(
                style=pc.get("style", "inline"),
                min_savings_ratio=float(pc.get("min_savings_ratio", 2.0)),
                min_abs_savings_if_none=int(pc.get("min_abs_savings_if_none", 5)),
            )

        if "budget" in d:
            bc = d["budget"]
            self.budget = BudgetConfig(
                max_tokens_per_file=bc.get("max_tokens_per_file"),
                priority_order=list(bc.get("priority_order", []))
            )
