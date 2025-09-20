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
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.engine import Engine
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions, ModelName
from lg.vcs import NullVcs
from tests.conftest import write  # используем уже существующий хелпер


# ====================== Типы для конфигурации ======================

@dataclass
class ModeConfig:
    """Конфигурация одного режима."""
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class ModeSetConfig:
    """Конфигурация набора режимов."""
    title: str
    modes: Dict[str, ModeConfig]

@dataclass
class TagConfig:
    """Конфигурация одного тега.""" 
    title: str
    description: str = ""

@dataclass
class TagSetConfig:
    """Конфигурация набора тегов."""
    title: str
    tags: Dict[str, TagConfig]


# ====================== Хелперы для создания конфигурации ======================

def write_modes_yaml(root: Path, mode_sets: Dict[str, ModeSetConfig], include: Optional[List[str]] = None, append: bool = False) -> Path:
    """
    Создает файл modes.yaml с указанными наборами режимов.
    
    Args:
        root: Корень проекта
        mode_sets: Словарь наборов режимов
        include: Список дочерних скоупов для включения
        append: Если True, дополняет существующую конфигурацию
        
    Returns:
        Путь к созданному файлу
    """
    from ruamel.yaml import YAML
    
    modes_file = root / "lg-cfg" / "modes.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    # Загружаем существующую конфигурацию если append=True
    existing_data = {}
    if append and modes_file.exists():
        with modes_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}
    
    # Преобразуем наши mode_sets в формат YAML
    new_data = {}
    
    if mode_sets:
        new_mode_sets = {}
        for set_name, mode_set in mode_sets.items():
            modes_dict = {}
            for mode_name, mode in mode_set.modes.items():
                mode_dict = {"title": mode.title}
                if mode.description:
                    mode_dict["description"] = mode.description
                if mode.tags:
                    mode_dict["tags"] = mode.tags
                mode_dict.update(mode.options)
                modes_dict[mode_name] = mode_dict
            
            new_mode_sets[set_name] = {
                "title": mode_set.title,
                "modes": modes_dict
            }
        new_data["mode-sets"] = new_mode_sets
    
    if include:
        new_data["include"] = include
    
    # Объединяем с существующими данными если append=True
    if append:
        if "mode-sets" in existing_data and "mode-sets" in new_data:
            existing_data["mode-sets"].update(new_data["mode-sets"])
        elif "mode-sets" in new_data:
            existing_data["mode-sets"] = new_data["mode-sets"]
        
        if "include" in new_data:
            existing_data["include"] = new_data["include"]
        
        final_data = existing_data
    else:
        final_data = new_data
    
    # Записываем обратно
    modes_file.parent.mkdir(parents=True, exist_ok=True)
    with modes_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)
    
    return modes_file


def write_tags_yaml(
    root: Path, 
    tag_sets: Optional[Dict[str, TagSetConfig]] = None,
    global_tags: Optional[Dict[str, TagConfig]] = None, 
    include: Optional[List[str]] = None,
    append: bool = False
) -> Path:
    """
    Создает файл tags.yaml с указанными наборами тегов.
    
    Args:
        root: Корень проекта
        tag_sets: Словарь наборов тегов
        global_tags: Словарь глобальных тегов
        include: Список дочерних скоупов для включения
        append: Если True, дополняет существующую конфигурацию
        
    Returns:
        Путь к созданному файлу
    """
    from ruamel.yaml import YAML
    
    tags_file = root / "lg-cfg" / "tags.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    # Загружаем существующую конфигурацию если append=True
    existing_data = {}
    if append and tags_file.exists():
        with tags_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}
    
    # Преобразуем наши данные в формат YAML
    new_data = {}
    
    if tag_sets:
        new_tag_sets = {}
        for set_name, tag_set in tag_sets.items():
            tags_dict = {}
            for tag_name, tag in tag_set.tags.items():
                tag_dict = {"title": tag.title}
                if tag.description:
                    tag_dict["description"] = tag.description
                tags_dict[tag_name] = tag_dict
            
            new_tag_sets[set_name] = {
                "title": tag_set.title,
                "tags": tags_dict
            }
        new_data["tag-sets"] = new_tag_sets
    
    if global_tags:
        new_global_tags = {}
        for tag_name, tag in global_tags.items():
            tag_dict = {"title": tag.title}
            if tag.description:
                tag_dict["description"] = tag.description
            new_global_tags[tag_name] = tag_dict
        new_data["tags"] = new_global_tags
    
    if include:
        new_data["include"] = include
    
    # Объединяем с существующими данными если append=True
    if append:
        if "tag-sets" in existing_data and "tag-sets" in new_data:
            existing_data["tag-sets"].update(new_data["tag-sets"])
        elif "tag-sets" in new_data:
            existing_data["tag-sets"] = new_data["tag-sets"]
        
        if "tags" in existing_data and "tags" in new_data:
            existing_data["tags"].update(new_data["tags"])
        elif "tags" in new_data:
            existing_data["tags"] = new_data["tags"]
        
        if "include" in new_data:
            existing_data["include"] = new_data["include"]
        
        final_data = existing_data
    else:
        final_data = new_data
    
    # Записываем обратно
    tags_file.parent.mkdir(parents=True, exist_ok=True)
    with tags_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)
    
    return tags_file


def create_basic_sections_yaml(root: Path) -> Path:
    """Создает базовый sections.yaml для тестов."""
    content = textwrap.dedent("""
    src:
      extensions: [".py", ".md"]
      code_fence: true
      filters:
        mode: allow
        allow:
          - "/src/**"
    
    docs:
      extensions: [".md"]
      code_fence: false
      markdown:
        max_heading_level: 2
      filters:
        mode: allow  
        allow:
          - "/docs/**"
    
    tests:
      extensions: [".py"]
      code_fence: true
      filters:
        mode: allow
        allow:
          - "/tests/**"
    """).strip() + "\n"
    
    return write(root / "lg-cfg" / "sections.yaml", content)


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
    Создает RunOptions с указанными параметрами.
    
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
    
    return RunContext(
        root=root,
        options=options,
        cache=cache,
        vcs=NullVcs(),
        tokenizer=default_tokenizer(),
        adaptive_loader=AdaptiveConfigLoader(root)
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


def render_for_test(root: Path, target: str, options: Optional[RunOptions] = None) -> str:
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
    write_modes_yaml(root, mode_sets)
    
    # Создаем конфигурацию тегов
    tag_sets, global_tags = get_default_tags_config()
    write_tags_yaml(root, tag_sets, global_tags)
    
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
    write_modes_yaml(root, mode_sets)
    
    # Минимальная конфигурация тегов
    global_tags = {
        "minimal": TagConfig(title="Минимальная версия")
    }
    write_tags_yaml(root, global_tags=global_tags)
    
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
    write_modes_yaml(root, root_modes, include=["apps/web", "libs/core"])
    
    # Корневая конфигурация тегов
    root_tags = {
        "full-context": TagConfig(title="Полный контекст")
    }
    write_tags_yaml(root, global_tags=root_tags, include=["apps/web", "libs/core"])
    
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
    write_modes_yaml(root / "apps" / "web", web_modes)
    
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
    write_tags_yaml(root / "apps" / "web", web_tag_sets, web_global_tags)
    
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
    write_modes_yaml(root / "libs" / "core", core_modes)
    
    core_global_tags = {
        "python": TagConfig(title="Python код"),
        "api-only": TagConfig(title="Только публичный API"),
        "full-impl": TagConfig(title="Полная реализация")
    }
    write_tags_yaml(root / "libs" / "core", global_tags=core_global_tags)
    
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
    "write_modes_yaml", "write_tags_yaml", "create_basic_sections_yaml",
    
    # Готовые конфигурации
    "get_default_modes_config", "get_default_tags_config",
    
    # Хелперы для RunOptions и контекстов
    "make_run_options", "make_run_context", "make_engine", "render_for_test",
    
    # Основные фикстуры
    "adaptive_project", "minimal_adaptive_project", "federated_project",
    
    # Хелперы для шаблонов
    "create_conditional_template", "create_mode_template"
]