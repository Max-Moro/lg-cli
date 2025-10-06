"""
AST узел для task-плейсхолдера.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..nodes import TemplateNode


@dataclass(frozen=True)
class TaskNode(TemplateNode):
    """
    Плейсхолдер для текста задачи ${task} или ${task:prompt:"..."}.
    
    Attributes:
        default_prompt: Дефолтное значение, если task не задан (None для простого ${task})
    """
    default_prompt: Optional[str] = None
    
    def canon_key(self) -> str:
        """Возвращает канонический ключ для кэширования."""
        if self.default_prompt:
            # Экранируем кавычки и обрезаем для читаемости
            escaped = self.default_prompt.replace('"', '\\"')[:50]
            return f'task:prompt:"{escaped}"'
        return "task"


__all__ = ["TaskNode"]