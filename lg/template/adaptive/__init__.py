"""
Plugin for adaptive template features.

Handles:
- {% if condition %}...{% elif condition %}...{% else %}...{% endif %} - conditional blocks
- {% mode modeset:mode %}...{% endmode %} - mode blocks
- {# comment #} - comments
- Logical operators: AND, OR, NOT
- Condition operators: tag:name, TAGSET:set:tag, scope:local
"""

from __future__ import annotations

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
from .plugin import AdaptivePlugin
from .processor_rules import get_adaptive_processor_rules, AdaptiveProcessorRules

__all__ = [
    "AdaptivePlugin",
    "ConditionalBlockNode",
    "ElifBlockNode", 
    "ElseBlockNode",
    "ModeBlockNode",
    "CommentNode",
    "get_adaptive_processor_rules",
    "AdaptiveProcessorRules"
]

