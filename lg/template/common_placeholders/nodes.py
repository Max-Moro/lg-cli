"""
AST узлы для базовых плейсхолдеров секций и шаблонов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from ..nodes import TemplateNode
from ...types import SectionRef


@dataclass(frozen=True)
class SectionNode(TemplateNode):
    """
    Плейсхолдер секции ${section}.
    
    Представляет ссылку на секцию, которая должна быть разрешена
    и заменена на отрендеренное содержимое секции.
    """
    section_name: str
    # Резолвленная ссылка на секцию (заполняется резолвером)
    resolved_ref: Optional[SectionRef] = None


@dataclass(frozen=True)
class IncludeNode(TemplateNode):
    """
    Плейсхолдер для включения шаблона ${tpl:name} или ${ctx:name}.
    
    Представляет ссылку на другой шаблон или контекст, который должен
    быть загружен, обработан и включен в текущее место.
    """
    kind: str  # "tpl" или "ctx"
    name: str
    origin: str  # "self" для локальных, или путь к скоупу для адресных
    
    # Включаемое содержимое (заполняется резолвером)
    children: Optional[List[TemplateNode]] = None

    def canon_key(self) -> str:
        """
        Возвращает канонический ключ для кэширования.
        """
        if self.origin == "self":
            return f"{self.kind}:{self.name}"
        else:
            return f"{self.kind}@{self.origin}:{self.name}"


__all__ = ["SectionNode", "IncludeNode"]