"""
Тестовая инфраструктура для адаптивных возможностей.

Предоставляет фикстуры для создания временных проектов с настроенными
режимами, тегами и федеративной структурой для тестирования адаптивной
системы Listing Generator.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass, field

import pytest

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.engine import Engine
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions, ModelName
from lg.vcs import NullVcs

# Импортируем из унифицированной инфраструктуры
from tests.infrastructure import (
    write, create_modes_yaml, create_tags_yaml, create_basic_sections_yaml,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig,
    make_run_options as base_make_run_options
)


# ====================== Хелперы для создания конфигурации ======================
# Все YAML билдеры теперь импортированы из tests.infrastructure


# create_tags_yaml и create_basic_sections_yaml теперь импортированы из infrastructure


# ====================== Готовые конфигурации ======================

def get_default_modes_config() -> Dict[str, ModeSetConfig]:
    """Возвращает стандартную конфигурацию режимов для тестов."""
    return {
        "ai-interaction": ModeSetConfig(
            title="Способ работы с AI",
            modes={
                "ask": ModeConfig(
                    title="Спросить",
                    description="Базовый режим вопрос-ответ"
                ),
                "agent": ModeConfig(
                    title="Агентная работа",
                    description="Режим с инструментами",
                    tags=["agent", "tools"],
                    options={"allow_tools": True}
                )
            }
        ),
        "dev-stage": ModeSetConfig(
            title="Стадия работы над фичей",
            modes={
                "planning": ModeConfig(
                    title="Планирование",
                    tags=["architecture", "docs"]
                ),
                "development": ModeConfig(
                    title="Основная разработка"
                ),
                "testing": ModeConfig(
                    title="Написание тестов",
                    tags=["tests"]
                ),
                "review": ModeConfig(
                    title="Кодревью", 
                    tags=["review"],
                    options={"vcs_mode": "changes"}
                )
            }
        )
    }


def get_default_tags_config() -> tuple[Dict[str, TagSetConfig], Dict[str, TagConfig]]:
    """Возвращает стандартную конфигурацию тегов для тестов."""
    tag_sets = {
        "language": TagSetConfig(
            title="Языки программирования",
            tags={
                "python": TagConfig(title="Python"),
                "typescript": TagConfig(title="TypeScript"),
                "javascript": TagConfig(title="JavaScript")
            }
        ),
        "code-type": TagSetConfig(
            title="Тип кода",
            tags={
                "product": TagConfig(title="Продуктовый код"),
                "tests": TagConfig(title="Тестовый код"),
                "generated": TagConfig(title="Сгенерированный код")
            }
        )
    }
    
    global_tags = {
        "agent": TagConfig(title="Агентные возможности"),
        "review": TagConfig(title="Правила проведения кодревью"),
        "architecture": TagConfig(title="Архитектурная документация"),
        "docs": TagConfig(title="Документация"),
        "tests": TagConfig(title="Тестовый код"),
        "tools": TagConfig(title="Инструменты"),
        "minimal": TagConfig(title="Минимальная версия")
    }
    
    return tag_sets, global_tags


# ====================== Хелперы для RunOptions ======================

def make_run_options(
    model: str = "o3",
    modes: Optional[Dict[str, str]] = None,
    extra_tags: Optional[Set[str]] = None
) -> RunOptions:
    """
    Создает RunOptions с указанными параметрами для адаптивных тестов.
    
    Args:
        model: Модель для токенизации
        modes: Словарь активных режимов {modeset: mode}
        extra_tags: Дополнительные теги
        
    Returns:
        Настроенный RunOptions
    """
    # Используем базовую функцию с адаптацией типов
    return base_make_run_options(
        model=model,
        modes=modes,
        extra_tags=extra_tags or set()
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
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        return Engine(options)
    finally:
        os.chdir(original_cwd)


def render_template(root: Path, target: str, options: Optional[RunOptions] = None) -> str:
    """
    Хелпер для рендеринга в тестах.
    
    Args:
        root: Корень проекта
        target: Цель для рендеринга
        options: Опции выполнения
        
    Returns:
        Отрендеренный текст
    """
    from lg.engine import _parse_target
    
    if options is None:
        options = make_run_options()
    
    engine = make_engine(root, options)
    target_spec = _parse_target(target, root)
    return engine.render_text(target_spec)


# ====================== Основные фикстуры ======================

@pytest.fixture
def adaptive_project(tmp_path: Path) -> Path:
    """
    Создает базовый проект с адаптивными возможностями.
    
    Включает:
    - Стандартные режимы и теги
    - Базовые секции
    - Несколько исходных файлов для тестирования
    """
    root = tmp_path
    
    # Создаем конфигурацию режимов
    mode_sets = get_default_modes_config()
    create_modes_yaml(root, mode_sets)
    
    # Создаем конфигурацию тегов
    tag_sets, global_tags = get_default_tags_config()
    create_tags_yaml(root, tag_sets, global_tags)
    
    # Создаем базовые секции
    create_basic_sections_yaml(root)
    
    # Создаем тестовые файлы
    write(root / "src" / "main.py", "def main():\n    print('Hello, world!')\n")
    write(root / "src" / "utils.py", "def helper():\n    return 42\n")
    write(root / "docs" / "README.md", "# Project Documentation\n\nThis is a test project.\n")
    write(root / "tests" / "test_main.py", "def test_main():\n    assert True\n")
    
    return root


@pytest.fixture
def minimal_adaptive_project(tmp_path: Path) -> Path:
    """
    Создает минимальный проект с одним режимом и тегом.
    Полезно для простых тестов.
    """
    root = tmp_path
    
    # Минимальная конфигурация режимов
    mode_sets = {
        "simple": ModeSetConfig(
            title="Простой режим",
            modes={
                "default": ModeConfig(title="По умолчанию"),
                "minimal": ModeConfig(
                    title="Минимальный",
                    tags=["minimal"]
                )
            }
        )
    }
    create_modes_yaml(root, mode_sets)
    
    # Минимальная конфигурация тегов
    global_tags = {
        "minimal": TagConfig(title="Минимальная версия")
    }
    create_tags_yaml(root, global_tags=global_tags)
    
    # Простая секция
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    all:
      extensions: [".py"]
      code_fence: true
      filters:
        mode: allow
        allow:
          - "/**"
    """).strip() + "\n")
    
    # Один тестовый файл
    write(root / "main.py", "print('minimal')\n")
    
    return root


@pytest.fixture  
def federated_project(tmp_path: Path) -> Path:
    """
    Создает проект с федеративной структурой (монорепо).
    
    Включает:
    - Корневой lg-cfg с базовой конфигурацией
    - Дочерний скоуп apps/web с собственной конфигурацией
    - Дочерний скоуп libs/core с собственной конфигурацией
    - Взаимные включения между скоупами
    """
    root = tmp_path
    
    # Корневая конфигурация режимов с включениями
    root_modes = {
        "workflow": ModeSetConfig(
            title="Рабочий процесс",
            modes={
                "full": ModeConfig(
                    title="Полный обзор",
                    tags=["full-context"]
                )
            }
        )
    }
    create_modes_yaml(root, root_modes, include=["apps/web", "libs/core"])
    
    # Корневая конфигурация тегов
    root_tags = {
        "full-context": TagConfig(title="Полный контекст")
    }
    create_tags_yaml(root, global_tags=root_tags, include=["apps/web", "libs/core"])
    
    # Корневые секции
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    overview:
      extensions: [".md"]
      code_fence: false
      filters:
        mode: allow
        allow:
          - "/README.md"
          - "/docs/**"
    """).strip() + "\n")
    
    # === Дочерний скоуп: apps/web ===
    web_modes = {
        "frontend": ModeSetConfig(
            title="Фронтенд работа",
            modes={
                "ui": ModeConfig(
                    title="UI компоненты",
                    tags=["typescript", "ui"]
                ),
                "api": ModeConfig(
                    title="API интеграция", 
                    tags=["typescript", "api"]
                )
            }
        )
    }
    create_modes_yaml(root / "apps" / "web", web_modes)
    
    web_tag_sets = {
        "frontend-type": TagSetConfig(
            title="Тип фронтенд кода",
            tags={
                "ui": TagConfig(title="UI компоненты"),
                "api": TagConfig(title="API слой")
            }
        )
    }
    web_global_tags = {
        "typescript": TagConfig(title="TypeScript код")
    }
    create_tags_yaml(root / "apps" / "web", web_tag_sets, web_global_tags)
    
    write(root / "apps" / "web" / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    web-src:
      extensions: [".ts", ".tsx"]
      code_fence: true
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n")
    
    # === Дочерний скоуп: libs/core ===
    core_modes = {
        "library": ModeSetConfig(
            title="Библиотечная разработка",
            modes={
                "public-api": ModeConfig(
                    title="Публичный API",
                    tags=["python", "api-only"]
                ),
                "internals": ModeConfig(
                    title="Внутренняя реализация",
                    tags=["python", "full-impl"]
                )
            }
        )
    }
    create_modes_yaml(root / "libs" / "core", core_modes)
    
    core_global_tags = {
        "python": TagConfig(title="Python код"),
        "api-only": TagConfig(title="Только публичный API"),
        "full-impl": TagConfig(title="Полная реализация")
    }
    create_tags_yaml(root / "libs" / "core", global_tags=core_global_tags)
    
    write(root / "libs" / "core" / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    core-lib:
      extensions: [".py"]
      code_fence: true
      python:
        when:
          - condition: "tag:api-only"
            strip_function_bodies: true
      filters:
        mode: allow
        allow:
          - "/core/**"
    """).strip() + "\n")
    
    # Тестовые файлы
    write(root / "README.md", "# Federated Project\n\nMain project documentation.\n")
    write(root / "docs" / "arch.md", "# Architecture\n\nSystem architecture overview.\n")
    write(root / "apps" / "web" / "src" / "App.tsx", "export function App() { return <div>Hello</div>; }\n")
    write(root / "libs" / "core" / "core" / "__init__.py", "def public_api():\n    return _internal()\n\ndef _internal():\n    return 'core'\n")
    
    return root


# ====================== Хелперы для шаблонов ======================

def create_conditional_template(
    root: Path,
    name: str,
    content: str,
    template_type: str = "ctx"
) -> Path:
    """
    Создает шаблон с условной логикой.
    
    Args:
        root: Корень проекта
        name: Имя шаблона (без расширения)
        content: Содержимое шаблона с условными блоками
        template_type: Тип шаблона ("ctx" или "tpl")
        
    Returns:
        Путь к созданному файлу
    """
    suffix = f".{template_type}.md"
    return write(root / "lg-cfg" / f"{name}{suffix}", content)


def create_mode_template(
    root: Path, 
    name: str,
    sections_by_mode: Dict[str, List[str]],
    template_type: str = "ctx"
) -> Path:
    """
    Создает шаблон с блоками режимов.
    
    Args:
        root: Корень проекта
        name: Имя шаблона
        sections_by_mode: Словарь {mode_spec: [section_names]}
        template_type: Тип шаблона
        
    Returns:
        Путь к созданному файлу
    """
    content_parts = [f"# Template {name}\n"]
    
    for mode_spec, sections in sections_by_mode.items():
        content_parts.append(f"\n{{% mode {mode_spec} %}}")
        for section in sections:
            content_parts.append(f"${{{section}}}")
        content_parts.append("{% endmode %}\n")
    
    content = "\n".join(content_parts)
    return create_conditional_template(root, name, content, template_type)


# ====================== Экспорты ======================

__all__ = [
    # Типы конфигурации
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
    
    # Хелперы для создания конфигурации
    "create_modes_yaml", "create_tags_yaml", "create_basic_sections_yaml",
    
    # Готовые конфигурации
    "get_default_modes_config", "get_default_tags_config",
    
    # Хелперы для RunOptions и контекстов
    "make_run_options", "make_run_context", "make_engine", "render_template",
    
    # Основные фикстуры
    "adaptive_project", "minimal_adaptive_project", "federated_project",
    
    # Хелперы для шаблонов
    "create_conditional_template", "create_mode_template"
]