"""
Тестовая инфраструктура для плейсхолдеров секций и шаблонов.

Предоставляет фикстуры и хелперы для создания временных проектов
с секциями, шаблонами и контекстами для тестирования основного
функционала движка шаблонизации Listing Generator.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, Optional, Any

import pytest

from lg.engine import Engine
from lg.types import RunOptions, ModelName


# ====================== Хелперы для создания файлов ======================

def write(p: Path, text: str) -> Path:
    """Записывает текст в файл, создавая родительские директории при необходимости."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_source_file(p: Path, content: str, language: str = "python") -> Path:
    """
    Создает исходный файл с содержимым для конкретного языка.
    
    Args:
        p: Путь к файлу
        content: Содержимое файла
        language: Язык программирования для корректного комментария
        
    Returns:
        Путь к созданному файлу
    """
    comment_map = {
        "python": "# ",
        "typescript": "// ",
        "javascript": "// ",
        "java": "// ",
        "cpp": "// "
    }
    
    comment_prefix = comment_map.get(language, "# ")
    
    lines = [f"{comment_prefix}Source file: {p.name}", ""]
    
    if content:
        lines.append(content.strip())
    
    return write(p, "\n".join(lines) + "\n")


def create_sections_yaml(root: Path, sections_config: Dict[str, Dict[str, Any]]) -> Path:
    """
    Создает lg-cfg/sections.yaml с указанными секциями.
    
    Args:
        root: Корень проекта
        sections_config: Словарь конфигурации секций
        
    Returns:
        Путь к созданному файлу
    """
    from ruamel.yaml import YAML
    
    sections_file = root / "lg-cfg" / "sections.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    sections_file.parent.mkdir(parents=True, exist_ok=True)
    with sections_file.open("w", encoding="utf-8") as f:
        yaml.dump(sections_config, f)
    
    return sections_file


def create_section_fragment(root: Path, fragment_path: str, sections_config: Dict[str, Dict[str, Any]]) -> Path:
    """
    Создает фрагмент секций *.sec.yaml.
    
    Args:
        root: Корень проекта
        fragment_path: Путь к файлу фрагмента относительно lg-cfg/
        sections_config: Словарь конфигурации секций
        
    Returns:
        Путь к созданному файлу
    """
    from ruamel.yaml import YAML
    
    fragment_file = root / "lg-cfg" / f"{fragment_path}.sec.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    fragment_file.parent.mkdir(parents=True, exist_ok=True)
    with fragment_file.open("w", encoding="utf-8") as f:
        yaml.dump(sections_config, f)
    
    return fragment_file


def create_template(root: Path, name: str, content: str, template_type: str = "ctx") -> Path:
    """
    Создает шаблон или контекст.
    
    Args:
        root: Корень проекта
        name: Имя файла (без расширения)
        content: Содержимое шаблона
        template_type: Тип ("ctx" или "tpl")
        
    Returns:
        Путь к созданному файлу
    """
    suffix = f".{template_type}.md"
    return write(root / "lg-cfg" / f"{name}{suffix}", content)


# ====================== Хелперы для рендеринга ======================

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
        options = RunOptions(model=ModelName("o3"))
    
    # Создаем движок с правильной рабочей директорией
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(root)
        
        from lg.engine import _parse_target
        engine = Engine(options)
        target_spec = _parse_target(target, root)
        return engine.render_text(target_spec)
    finally:
        os.chdir(original_cwd)


def make_run_options(
    model: str = "o3",
    modes: Optional[Dict[str, str]] = None,
    extra_tags: Optional[set] = None
) -> RunOptions:
    """Создает RunOptions с указанными параметрами."""
    return RunOptions(
        model=ModelName(model),
        modes=modes or {},
        extra_tags=extra_tags or set()
    )


# ====================== Готовые конфигурации секций ======================

def get_basic_sections_config() -> Dict[str, Dict[str, Any]]:
    """Возвращает базовую конфигурацию секций для тестов."""
    return {
        "src": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        },
        "docs": {
            "extensions": [".md"],
            "code_fence": False,
            "markdown": {
                "max_heading_level": 2
            },
            "filters": {
                "mode": "allow",
                "allow": ["/docs/**"]
            }
        },
        "all": {
            "extensions": [".py", ".md", ".ts"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/**"]
            }
        },
        "tests": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/tests/**"]
            }
        }
    }


def get_multilang_sections_config() -> Dict[str, Dict[str, Any]]:
    """Возвращает конфигурацию секций для многоязычных проектов."""
    return {
        "python-src": {
            "extensions": [".py"],
            "code_fence": True,
            "python": {
                "skip_trivial_inits": True
            },
            "filters": {
                "mode": "allow",
                "allow": ["/python/**"]
            }
        },
        "typescript-src": {
            "extensions": [".ts", ".tsx"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/typescript/**"]
            }
        },
        "shared-docs": {
            "extensions": [".md"],
            "code_fence": False,
            "markdown": {
                "max_heading_level": 3
            },
            "filters": {
                "mode": "allow",
                "allow": ["/shared-docs/**"]
            }
        }
    }


# ====================== Основные фикстуры ======================

@pytest.fixture
def basic_project(tmp_path: Path) -> Path:
    """
    Создает базовый проект для тестирования плейсхолдеров секций и шаблонов.
    
    Включает:
    - Стандартные секции (src, docs, all, tests)
    - Несколько исходных файлов разных типов
    - Базовую структуру директорий
    """
    root = tmp_path
    
    # Создаем секции
    sections_config = get_basic_sections_config()
    create_sections_yaml(root, sections_config)
    
    # Создаем исходные файлы
    write_source_file(root / "src" / "main.py", 
                     "def main():\n    print('Hello from main')\n    return 0")
    
    write_source_file(root / "src" / "utils.py", 
                     "def helper_function(x):\n    return x * 2\n\nclass Helper:\n    pass")
    
    write_source_file(root / "src" / "config.py", 
                     "CONFIG = {\n    'app_name': 'test',\n    'version': '1.0.0'\n}")
    
    # Создаем документацию
    write(root / "docs" / "README.md", textwrap.dedent("""
        # Project Documentation
        
        This is the main project documentation.
        
        ## Features
        
        - Feature A: Core functionality
        - Feature B: Additional utilities
        
        ## Usage
        
        See the API reference for details.
        """).strip() + "\n")
    
    write(root / "docs" / "api.md", textwrap.dedent("""
        # API Reference
        
        ## Functions
        
        ### main()
        
        Main entry point.
        
        ### helper_function(x)
        
        Helper utility function.
        """).strip() + "\n")
    
    # Создаем тестовые файлы
    write_source_file(root / "tests" / "test_main.py", 
                     "def test_main():\n    assert True\n\ndef test_helper():\n    assert helper_function(2) == 4")
    
    return root


@pytest.fixture
def multilang_project(tmp_path: Path) -> Path:
    """
    Создает многоязычный проект для тестирования сложных конфигураций.
    
    Включает:
    - Файлы Python и TypeScript
    - Специализированные секции для разных языков
    - Shared документацию
    """
    root = tmp_path
    
    # Создаем специализированные секции
    sections_config = get_multilang_sections_config()
    create_sections_yaml(root, sections_config)
    
    # Python файлы
    write_source_file(root / "python" / "__init__.py", "", "python")
    write_source_file(root / "python" / "core.py", 
                     "class Core:\n    def process(self):\n        pass", "python")
    
    # TypeScript файлы
    write_source_file(root / "typescript" / "app.ts",
                     "export class App {\n  run(): void {\n    console.log('Running');\n  }\n}", "typescript")
    
    write_source_file(root / "typescript" / "utils.tsx",
                     "import React from 'react';\n\nexport const Component = () => <div>Hello</div>;", "typescript")
    
    # Общая документация
    write(root / "shared-docs" / "architecture.md", textwrap.dedent("""
        # Architecture Overview
        
        This project uses a multilingual approach:
        
        ## Backend (Python)
        
        Core business logic implementation.
        
        ## Frontend (TypeScript)
        
        User interface and interaction layer.
        """).strip() + "\n")
    
    return root


@pytest.fixture
def federated_project(tmp_path: Path) -> Path:
    """
    Создает федеративный проект (монорепо) для тестирования адресных ссылок.
    
    Включает:
    - Корневой lg-cfg с базовыми секциями
    - Дочерний скоуп apps/web с собственными секциями
    - Дочерний скоуп libs/core с собственными секциями
    - Взаимные зависимости между скоупами
    """
    root = tmp_path
    
    # === Корневые секции ===
    root_sections = {
        "overview": {
            "extensions": [".md"],
            "code_fence": False,
            "filters": {
                "mode": "allow",
                "allow": ["/README.md", "/docs/**"]
            }
        },
        "root-config": {
            "extensions": [".json", ".yaml"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/*.json", "/*.yaml"]
            }
        }
    }
    create_sections_yaml(root, root_sections)
    
    # Корневые файлы
    write(root / "README.md", textwrap.dedent("""
        # Federated Project
        
        This is a monorepo with multiple modules.
        
        ## Structure
        
        - apps/web - Web application
        - libs/core - Core library
        """).strip() + "\n")
    
    write(root / "docs" / "overview.md", textwrap.dedent("""
        # Project Overview
        
        Comprehensive project documentation.
        """).strip() + "\n")
    
    # === Дочерний скоуп: apps/web ===
    web_sections = {
        "web-src": {
            "extensions": [".ts", ".tsx"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        },
        "web-docs": {
            "extensions": [".md"],
            "code_fence": False,
            "filters": {
                "mode": "allow",
                "allow": ["/docs/**"]
            }
        }
    }
    create_sections_yaml(root / "apps" / "web", web_sections)
    
    write_source_file(root / "apps" / "web" / "src" / "App.tsx",
                     "export const App = () => <div>Web App</div>;", "typescript")
    
    write_source_file(root / "apps" / "web" / "src" / "utils.ts",
                     "export function webUtil() { return 'web'; }", "typescript")
    
    write(root / "apps" / "web" / "docs" / "deployment.md", textwrap.dedent("""
        # Web App Deployment
        
        Deployment instructions for the web application.
        """).strip() + "\n")
    
    # === Дочерний скоуп: libs/core ===
    core_sections = {
        "core-lib": {
            "extensions": [".py"],
            "code_fence": True,
            "python": {
                "skip_trivial_inits": True
            },
            "filters": {
                "mode": "allow",
                "allow": ["/core/**"]
            }
        },
        "core-api": {
            "extensions": [".py"],
            "code_fence": True,
            "python": {
                "strip_function_bodies": True
            },
            "filters": {
                "mode": "allow",
                "allow": ["/core/api/**"]
            }
        }
    }
    create_sections_yaml(root / "libs" / "core", core_sections)
    
    write_source_file(root / "libs" / "core" / "core" / "__init__.py", "", "python")
    
    write_source_file(root / "libs" / "core" / "core" / "processor.py",
                     "class Processor:\n    def process(self, data):\n        return data.upper()", "python")
    
    write_source_file(root / "libs" / "core" / "core" / "api" / "client.py",
                     "def get_client():\n    return CoreClient()\n\nclass CoreClient:\n    pass", "python")
    
    return root


@pytest.fixture
def fragments_project(tmp_path: Path) -> Path:
    """
    Создает проект с фрагментами секций для тестирования *.sec.yaml файлов.
    
    Включает:
    - Базовый sections.yaml
    - Несколько фрагментов в разных директориях
    - Секции с каноническими ID
    """
    root = tmp_path
    
    # Базовые секции
    base_sections = {
        "main": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/main.py"]
            }
        }
    }
    create_sections_yaml(root, base_sections)
    
    # Фрагмент с одной секцией (канонический ID = имя секции)
    fragment1 = {
        "database": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/db/**"]
            }
        }
    }
    create_section_fragment(root, "database", fragment1)
    
    # Фрагмент с несколькими секциями (канонический ID = prefix/section)
    fragment2 = {
        "auth": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/auth/**"]
            }
        },
        "permissions": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/permissions/**"]
            }
        }
    }
    create_section_fragment(root, "security/security", fragment2)
    
    # Фрагмент в подпапке
    fragment3 = {
        "api-v1": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/api/v1/**"]
            }
        }
    }
    create_section_fragment(root, "api/v1", fragment3)
    
    # Создаем файлы для всех секций
    write_source_file(root / "main.py", "print('main')", "python")
    write_source_file(root / "db" / "models.py", "class User: pass", "python")
    write_source_file(root / "auth" / "login.py", "def login(): pass", "python")
    write_source_file(root / "permissions" / "check.py", "def check(): pass", "python")
    write_source_file(root / "api" / "v1" / "handlers.py", "def handle(): pass", "python")
    
    return root


# ====================== Хелперы для сложных шаблонов ======================

def create_nested_template_structure(root: Path) -> Dict[str, Path]:
    """
    Создает структуру вложенных шаблонов и контекстов.
    
    Returns:
        Словарь с путями к созданным файлам
    """
    paths = {}
    
    # Базовые шаблоны
    paths["intro"] = create_template(root, "intro", """# Project Introduction

This is a generated introduction for the project.

## Key Features

- Modular architecture
- Extensible design
""", "tpl")
    
    paths["footer"] = create_template(root, "footer", """---

## Contact Information

For questions, contact the development team.
""", "tpl")
    
    # Составные шаблоны
    paths["full-docs"] = create_template(root, "full-docs", """${tpl:intro}

## Source Code

${src}

## Documentation

${docs}

${tpl:footer}
""", "tpl")
    
    # Контексты
    paths["basic-context"] = create_template(root, "basic-context", """# Basic Project Context

${tpl:full-docs}

## Test Suite

${tests}
""", "ctx")
    
    paths["simple-context"] = create_template(root, "simple-context", """# Simple Context

${src}
${docs}
""", "ctx")
    
    return paths


def create_complex_federated_templates(root: Path) -> Dict[str, Path]:
    """
    Создает сложную структуру шаблонов для федеративного проекта.
    
    Returns:
        Словарь с путями к созданным файлам
    """
    paths = {}
    
    # Корневые шаблоны
    paths["project-overview"] = create_template(root, "project-overview", """# Project Overview

${overview}

## Web Application
${@apps/web:web-docs}

## Core Library
${@libs/core:core-lib}
""", "tpl")
    
    # Шаблоны в дочерних скоупах
    paths["web-intro"] = create_template(root / "apps" / "web", "web-intro", """# Web Application

${web-src}

## Documentation
${web-docs}
""", "tpl")
    
    paths["core-api-docs"] = create_template(root / "libs" / "core", "api-docs", """# Core Library API

${core-api}
""", "tpl")
    
    # Контексты с cross-scope включениями
    paths["full-stack-context"] = create_template(root, "full-stack", """# Full Stack Context

${tpl:project-overview}

## Detailed Web Implementation
${tpl@apps/web:web-intro}

## Core API Reference
${tpl@libs/core:api-docs}
""", "ctx")
    
    return paths


# ====================== Экспорты ======================

__all__ = [
    # Основные фикстуры
    "basic_project", "multilang_project", "federated_project", "fragments_project",
    
    # Хелперы для создания файлов
    "write", "write_source_file", "create_sections_yaml", "create_section_fragment", "create_template",
    
    # Хелперы для рендеринга
    "render_template", "make_run_options",
    
    # Готовые конфигурации
    "get_basic_sections_config", "get_multilang_sections_config",
    
    # Хелперы для сложных структур
    "create_nested_template_structure", "create_complex_federated_templates"
]