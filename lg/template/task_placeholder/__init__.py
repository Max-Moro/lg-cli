"""
Плагин для обработки task-плейсхолдеров.

Обрабатывает:
- ${task} - простая вставка текста задачи
- ${task:prompt:"default text"} - вставка с дефолтным значением
"""

from __future__ import annotations

from .nodes import TaskNode
from .plugin import TaskPlaceholderPlugin

__all__ = ["TaskPlaceholderPlugin", "TaskNode"]