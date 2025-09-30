"""
Переиспользуемые фикстуры pytest для всех тестов.

Содержит основные фикстуры, которые могут использоваться в различных тестах.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Set

import pytest

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.engine import Engine
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions, ModelName
from lg.vcs import NullVcs

from .file_utils import write
from .rendering_utils import make_run_options


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """
    Базовая фикстура временного проекта.
    
    Создает минимальную структуру проекта для тестов.
    """
    root = tmp_path
    
    # Создаем базовую конфигурацию
    write(root / "lg-cfg" / "sections.yaml", """
all:
  extensions: [".py", ".md"]
  code_fence: true
  filters:
    mode: allow
    allow:
      - "/**"
""".strip() + "\n")
    
    return root


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


def mk_run_ctx(root: Path) -> RunContext:
    """
    Алиас для make_run_context для совместимости с cdm тестами.
    
    Args:
        root: Корень проекта
        
    Returns:
        RunContext с дефолтными настройками
    """
    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    return RunContext(
        root=root,
        options=RunOptions(),
        cache=cache,
        vcs=NullVcs(),
        tokenizer=default_tokenizer(),
        adaptive_loader=AdaptiveConfigLoader(root),
    )


__all__ = [
    "tmp_project", "make_run_context", "mk_run_ctx"
]