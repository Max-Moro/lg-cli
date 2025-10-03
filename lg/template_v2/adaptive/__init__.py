"""
Плагин для адаптивных возможностей шаблонизатора.

Обрабатывает:
- {% if condition %}...{% elif condition %}...{% else %}...{% endif %} - условные конструкции
- {% mode modeset:mode %}...{% endmode %} - режимные блоки
- {# комментарий #} - комментарии
- Логические операторы: AND, OR, NOT
- Операторы условий: tag:name, TAGSET:set:tag, scope:local
"""

from __future__ import annotations

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
from .plugin import AdaptivePlugin

__all__ = [
    "AdaptivePlugin",
    "ConditionalBlockNode",
    "ElifBlockNode", 
    "ElseBlockNode",
    "ModeBlockNode",
    "CommentNode"
]

