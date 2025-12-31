"""
AST nodes for basic section and template placeholders.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from ..nodes import TemplateNode
from ...types import SectionRef


@dataclass(frozen=True)
class SectionNode(TemplateNode):
    """
    Section placeholder ${section}.
    """
    name: str
    # Resolved section reference (filled by resolver)
    resolved_ref: Optional[SectionRef] = None


@dataclass(frozen=True)
class IncludeNode(TemplateNode):
    """
    Placeholder for including a template ${tpl:name} or ${ctx:name}.

    Represents a reference to another template or context that should
    be loaded, processed, and included in the current location.
    """
    kind: str  # "tpl" or "ctx"
    name: str
    origin: str  # "self" for local, or scope path for addressed

    # Included content (filled by resolver)
    children: Optional[List[TemplateNode]] = None

    # Resolved file path (filled by resolver, used for file_scope in processing)
    resolved_path: Optional[Path] = None

    def canon_key(self) -> str:
        """
        Returns canonical key for caching.
        """
        if self.origin == "self":
            return f"{self.kind}:{self.name}"
        else:
            return f"{self.kind}@{self.origin}:{self.name}"


__all__ = ["SectionNode", "IncludeNode"]