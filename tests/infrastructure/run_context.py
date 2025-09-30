"""
Переиспользуемые фикстуры pytest для всех тестов.

Содержит основные фикстуры, которые могут использоваться в различных тестах.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.vcs import NullVcs
from .rendering_utils import make_run_options


def make_run_context(root: Path, options: Optional[RunOptions] = None) -> RunContext:
    """
    Создает RunContext для тестирования.
    
    Args:
        root: Корень проекта
        options: Опции выполнения
        
    Returns:
        Настроенный RunContext
    """
    if options is None:
        options = make_run_options()
    
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    adaptive_loader = AdaptiveConfigLoader(root)
    
    # Используем process_adaptive_options для правильной инициализации active_tags
    active_tags, mode_options, _ = process_adaptive_options(
        root,
        options.modes,
        options.extra_tags
    )
    
    return RunContext(
        root=root,
        options=options,
        cache=cache,
        vcs=NullVcs(),
        tokenizer=default_tokenizer(),
        adaptive_loader=adaptive_loader,
        mode_options=mode_options,
        active_tags=active_tags
    )

__all__ = [
    "tmp_project", "make_run_context"
]