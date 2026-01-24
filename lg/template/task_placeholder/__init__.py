"""
Plugin for processing task placeholders.

Handles:
- ${task} - simple task text insertion
- ${task:prompt:"default text"} - insertion with default value
"""

from __future__ import annotations

from .nodes import TaskNode

__all__ = ["TaskNode"]