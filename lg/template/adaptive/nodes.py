"""
AST nodes for adaptive template features.

Defines nodes for conditional blocks, mode blocks, and comments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..nodes import TemplateNode
from ...conditions.model import Condition


@dataclass(frozen=True)
class ConditionalBlockNode(TemplateNode):
    """
    Conditional block {% if condition %}...{% elif condition %}...{% else %}...{% endif %}.

    Represents a conditional construct that includes or excludes content based on
    evaluation of a conditional expression with support for elif block chains.
    """
    condition_text: str  # Original condition text
    body: List[TemplateNode]
    elif_blocks: List['ElifBlockNode'] = field(default_factory=list)
    else_block: Optional['ElseBlockNode'] = None

    # Condition AST after parsing (filled by condition parser)
    condition_ast: Optional[Condition] = None


@dataclass(frozen=True)
class ElifBlockNode(TemplateNode):
    """
    Elif block {% elif condition %} within conditional constructs.

    Represents conditional alternative content that is checked if
    previous conditions in the if/elif chain did not succeed.
    """
    condition_text: str  # Original condition text
    body: List[TemplateNode]

    # Condition AST after parsing (filled by condition parser)
    condition_ast: Optional[Condition] = None


@dataclass(frozen=True)
class ElseBlockNode(TemplateNode):
    """
    Else block {% else %} within conditional constructs.

    Represents alternative content that is used if the condition
    in ConditionalBlockNode does not succeed.
    """
    body: List[TemplateNode]


@dataclass(frozen=True)
class ModeBlockNode(TemplateNode):
    """
    Mode override block {% mode modeset:mode %}...{% endmode %}.

    Represents a block within which a specific mode is active,
    overriding global settings for processing nested content.
    """
    modeset: str
    mode: str
    body: List[TemplateNode]


@dataclass(frozen=True)
class CommentNode(TemplateNode):
    """
    Comment block {# comment #}.

    Represents a comment in the template that is ignored
    during rendering and does not appear in the final result.
    """
    text: str


__all__ = [
    "ConditionalBlockNode",
    "ElifBlockNode",
    "ElseBlockNode", 
    "ModeBlockNode",
    "CommentNode"
]

