"""
Plugin for adaptive template features.

Handles:
- {% if condition %}...{% elif condition %}...{% else %}...{% endif %} - conditional blocks
- {% mode modeset:mode %}...{% endmode %} - mode blocks
- {# comment #} - comments
"""

from __future__ import annotations

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode

__all__ = [
    "ConditionalBlockNode",
    "ElifBlockNode",
    "ElseBlockNode",
    "ModeBlockNode",
    "CommentNode",
]

