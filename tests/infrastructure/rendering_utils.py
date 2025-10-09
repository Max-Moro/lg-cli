"""
Утилиты для рендеринга шаблонов и создания движков в тестах.

Унифицирует все rendering-__all__ = [
    "make_run_options", "make_engine", "render_template"
] различных conftest.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Set
from typing import Optional

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.engine import Engine
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.vcs import NullVcs


def make_run_options(
    modes: Optional[Dict[str, str]] = None,
    extra_tags: Optional[Set[str]] = None,
    task_text: Optional[str] = None
) -> RunOptions:
    """
    Создает RunOptions с указанными параметрами.
    
    Унифицированная функция для всех тестов.
    
    Args:
        model: Модель для токенизации
        modes: Словарь активных режимов {modeset: mode}  
        extra_tags: Дополнительные теги
        task_text: Текст текущей задачи
        
    Returns:
        Настроенный RunOptions
    """
    return RunOptions(
        modes=modes or {},
        extra_tags=extra_tags or set(),
        task_text=task_text
    )


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


def make_engine(root: Path, options: Optional[RunOptions] = None) -> Engine:
    """
    Создает Engine для тестирования.
    
    Args:
        root: Корень проекта  
        options: Опции выполнения
        
    Returns:
        Настроенный Engine
    """
    if options is None:
        options = make_run_options()
    
    # Временно меняем текущую директорию для Engine
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        return Engine(options)
    finally:
        os.chdir(original_cwd)


def render_template(root: Path, target: str, options: Optional[RunOptions] = None) -> str:
    """
    Рендерит шаблон или секцию в указанном проекте.
    
    Args:
        root: Корень проекта
        target: Цель рендеринга (ctx:name, sec:name или name)
        options: Опции выполнения
        
    Returns:
        Отрендеренный текст
    """
    if options is None:
        options = make_run_options()
    
    from lg.engine import _parse_target
    
    # Создаем движок с правильной рабочей директорией
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        engine = Engine(options)
        target_spec = _parse_target(target, root)
        return engine.render_text(target_spec)
    finally:
        os.chdir(original_cwd)


__all__ = [
    "make_run_options", "make_run_context", "make_engine", "render_template"
]