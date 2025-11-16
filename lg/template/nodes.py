"""
Base AST nodes.

Defines base hierarchy of immutable node classes for representing
template structure. Concrete nodes are defined in plugins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TemplateNode:
    """Base class for all template AST nodes."""
    pass


@dataclass(frozen=True)
class TextNode(TemplateNode):
    """
    Plain text content in template.

    Represents static text that requires no processing
    and is output as-is.
    """
    text: str


# Alias for node list (AST)
TemplateAST = List[TemplateNode]


__all__ = ["TemplateNode", "TextNode", "TemplateAST"]