"""
Базовые AST-узлы.

Определяет базовую иерархию неизменяемых классов узлов для представления
структуры шаблонов. Конкретные узлы определяются в плагинах.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TemplateNode:
    """Базовый класс для всех узлов AST шаблона."""
    pass


@dataclass(frozen=True)
class TextNode(TemplateNode):
    """
    Обычный текстовый контент в шаблоне.
    
    Представляет статический текст, который не требует обработки
    и выводится в результат как есть.
    """
    text: str


# Алиас для списка узлов (AST)
TemplateAST = List[TemplateNode]


__all__ = ["TemplateNode", "TextNode", "TemplateAST"]