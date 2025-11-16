"""
AST node for task placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..nodes import TemplateNode


@dataclass(frozen=True)
class TaskNode(TemplateNode):
    """
    Placeholder for task text ${task} or ${task:prompt:"..."}.

    Attributes:
        default_prompt: Default value if task not set (None for simple ${task})
    """
    default_prompt: Optional[str] = None

    def canon_key(self) -> str:
        """Returns canonical key for caching."""
        if self.default_prompt:
            # Escape quotes and truncate for readability
            escaped = self.default_prompt.replace('"', '\\"')[:50]
            return f'task:prompt:"{escaped}"'
        return "task"


__all__ = ["TaskNode"]