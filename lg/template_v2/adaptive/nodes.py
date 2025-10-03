"""
AST узлы для адаптивных возможностей шаблонизатора.

Определяет узлы для условных конструкций, режимных блоков и комментариев.
Портированы из lg.template.nodes с адаптацией под модульную архитектуру.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ..nodes import TemplateNode
from ...conditions.model import Condition
from ...config.adaptive_model import ModeOptions


@dataclass(frozen=True)
class ConditionalBlockNode(TemplateNode):
    """
    Условный блок {% if condition %}...{% elif condition %}...{% else %}...{% endif %}.
    
    Представляет условную конструкцию, которая включает или исключает
    содержимое на основе вычисления условного выражения с поддержкой 
    цепочек elif блоков.
    """
    condition_text: str  # Исходный текст условия
    body: List[TemplateNode]
    elif_blocks: List['ElifBlockNode'] = field(default_factory=list)
    else_block: Optional['ElseBlockNode'] = None
    
    # AST условия после парсинга (заполняется парсером условий)
    condition_ast: Optional[Condition] = None
    # Результат вычисления (заполняется во время оценки)
    evaluated: Optional[bool] = None


@dataclass(frozen=True)
class ElifBlockNode(TemplateNode):
    """
    Блок {% elif condition %} внутри условных конструкций.
    
    Представляет условное альтернативное содержимое, которое проверяется
    если предыдущие условия в цепочке if/elif не выполнились.
    """
    condition_text: str  # Исходный текст условия
    body: List[TemplateNode]
    
    # AST условия после парсинга (заполняется парсером условий)
    condition_ast: Optional[Condition] = None
    # Результат вычисления (заполняется во время оценки)
    evaluated: Optional[bool] = None


@dataclass(frozen=True)
class ElseBlockNode(TemplateNode):
    """
    Блок {% else %} внутри условных конструкций.
    
    Представляет альтернативное содержимое, которое используется
    если условие в ConditionalBlockNode не выполняется.
    """
    body: List[TemplateNode]


@dataclass(frozen=True)
class ModeBlockNode(TemplateNode):
    """
    Блок переопределения режима {% mode modeset:mode %}...{% endmode %}.
    
    Представляет блок, внутри которого активен определенный режим,
    переопределяющий глобальные настройки для обработки вложенного содержимого.
    """
    modeset: str
    mode: str
    body: List[TemplateNode]
    
    # Сохраненное состояние контекста (заполняется во время выполнения)
    original_mode_options: Optional[ModeOptions] = None
    original_active_tags: Optional[Set[str]] = None
    original_active_modes: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class CommentNode(TemplateNode):
    """
    Блок комментария {# комментарий #}.
    
    Представляет комментарий в шаблоне, который игнорируется 
    при рендеринге и не попадает в итоговый результат.
    """
    text: str


__all__ = [
    "ConditionalBlockNode",
    "ElifBlockNode",
    "ElseBlockNode", 
    "ModeBlockNode",
    "CommentNode"
]

