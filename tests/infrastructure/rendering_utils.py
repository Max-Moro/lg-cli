"""
Утилиты для рендеринга шаблонов и создания движков в тестах.

Унифицирует все rendering-__all__ = [
    "make_run_options", "make_engine", "render_template"
] различных conftest.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Set

from lg.engine import Engine
from lg.types import RunOptions, ModelName


def make_run_options(
    model: str = "o3",
    modes: Optional[Dict[str, str]] = None,
    extra_tags: Optional[Set[str]] = None
) -> RunOptions:
    """
    Создает RunOptions с указанными параметрами.
    
    Унифицированная функция для всех тестов.
    
    Args:
        model: Модель для токенизации
        modes: Словарь активных режимов {modeset: mode}  
        extra_tags: Дополнительные теги
        
    Returns:
        Настроенный RunOptions
    """
    return RunOptions(
        model=ModelName(model),
        modes=modes or {},
        extra_tags=extra_tags or set()
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
    "make_run_options", "make_engine", "render_template"
]