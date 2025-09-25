"""
Тестовая инфраструктура для md-плейсхолдеров.

Предоставляет фикстуры и хелперы для создания временных проектов
с Markdown-файлами и тестирования md-плейсхолдеров типа ${md:...}.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, Optional

import pytest

from lg.engine import Engine
from lg.types import RunOptions, ModelName


# ====================== Хелперы для создания файлов ======================

def write(p: Path, text: str) -> Path:
    """Записывает текст в файл, создавая родительские директории при необходимости."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_markdown(p: Path, title: str = "", content: str = "", h1_prefix: str = "# ") -> Path:
    """
    Создает Markdown-файл с заголовком и содержимым.
    
    Args:
        p: Путь к файлу
        title: Заголовок (если задан, добавляется как H1)
        content: Основное содержимое
        h1_prefix: Префикс для H1 заголовка (позволяет создавать файлы без H1)
        
    Returns:
        Путь к созданному файлу
    """
    lines = []
    
    if title:
        lines.append(f"{h1_prefix}{title}")
        lines.append("")  # пустая строка после заголовка
    
    if content:
        lines.append(content.strip())
    
    return write(p, "\n".join(lines) + "\n")


def create_basic_lg_cfg(root: Path, *, code_fence: bool = True) -> Path:
    """Создает минимальную конфигурацию lg-cfg/sections.yaml."""
    content = textwrap.dedent(f"""
    all:
      extensions: [".md"]
      code_fence: {str(code_fence).lower()}
      markdown:
        max_heading_level: 2
      filters:
        mode: allow
        allow:
          - "/**"
    """).strip() + "\n"
    
    return write(root / "lg-cfg" / "sections.yaml", content)


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


# ====================== Основные фикстуры ======================

@pytest.fixture
def md_project(tmp_path: Path) -> Path:
    """
    Создает базовый проект для тестирования md-плейсхолдеров.
    
    Включает:
    - Минимальную конфигурацию lg-cfg
    - Несколько тестовых Markdown-файлов
    - Базовую структуру директорий
    """
    root = tmp_path
    
    # Создаем базовую конфигурацию
    create_basic_lg_cfg(root)
    
    # Создаем тестовые Markdown-файлы
    write_markdown(root / "README.md", 
                  title="Main Project", 
                  content="This is the main project documentation.\n\n## Features\n\n- Feature A\n- Feature B")
    
    write_markdown(root / "docs" / "guide.md", 
                  title="User Guide", 
                  content="This is a comprehensive user guide.\n\n## Installation\n\nRun the installer.\n\n## Usage\n\nUse the app.")
    
    write_markdown(root / "docs" / "api.md",
                  title="API Reference", 
                  content="API documentation.\n\n## Authentication\n\nUse API keys.\n\n## Endpoints\n\n### GET /users\n\nGet users list.")
    
    # Файл без H1 для тестов strip_h1
    write_markdown(root / "docs" / "changelog.md",
                  title="", 
                  content="## v1.0.0\n\n- Initial release\n\n## v0.9.0\n\n- Beta version")
    
    # Файл в lg-cfg для тестов @self:
    write_markdown(root / "lg-cfg" / "internal.md",
                  title="Internal Documentation",
                  content="This is internal documentation stored in lg-cfg.")
    
    return root


@pytest.fixture  
def federated_md_project(tmp_path: Path) -> Path:
    """
    Создает проект с федеративной структурой для тестирования адресных md-плейсхолдеров.
    
    Включает:
    - Корневой lg-cfg с базовой конфигурацией
    - Дочерний скоуп apps/web с собственными документами
    - Дочерний скоуп libs/utils с собственными документами  
    """
    root = tmp_path
    
    # Корневая конфигурация
    create_basic_lg_cfg(root)
    
    # Корневые документы
    write_markdown(root / "README.md", 
                  title="Federated Project", 
                  content="Main project in a monorepo structure.")
    
    # Внутренняя документация в lg-cfg
    write_markdown(root / "lg-cfg" / "internal.md",
                  title="Internal Documentation",
                  content="Internal documentation for the federated project.")
    
    # === Дочерний скоуп: apps/web ===
    create_basic_lg_cfg(root / "apps" / "web")
    
    write_markdown(root / "apps" / "web" / "web-readme.md",
                  title="Web Application",
                  content="Frontend web application.\n\n## Components\n\n- Header\n- Footer\n- Main content")
    
    write_markdown(root / "apps" / "web" / "lg-cfg" / "deployment.md",
                  title="Web Deployment Guide", 
                  content="How to deploy the web app.\n\n## Build\n\nnpm run build\n\n## Deploy\n\nDeploy to staging.")
    
    # === Дочерний скоуп: libs/utils ===  
    create_basic_lg_cfg(root / "libs" / "utils")
    
    write_markdown(root / "libs" / "utils" / "utils-readme.md",
                  title="Utility Library",
                  content="Shared utility functions.\n\n## Math Utils\n\n- add()\n- multiply()\n\n## String Utils\n\n- capitalize()\n- trim()")
    
    return root


@pytest.fixture
def adaptive_md_project(tmp_path: Path) -> Path:
    """
    Создает проект с поддержкой адаптивных возможностей для тестирования условных md-плейсхолдеров.
    """
    root = tmp_path
    
    # Создаем базовую конфигурацию
    create_basic_lg_cfg(root)
    
    # Конфигурация тегов
    write(root / "lg-cfg" / "tags.yaml", textwrap.dedent("""
    tags:
      cloud:
        title: "Cloud deployment"
      onprem:
        title: "On-premises deployment"
      basic:
        title: "Basic documentation"
    """).strip() + "\n")
    
    # Создаем документы для условного включения
    write_markdown(root / "deployment" / "cloud.md",
                  title="Cloud Deployment",
                  content="Instructions for cloud deployment.\n\n## AWS\n\nUse CloudFormation.\n\n## Azure\n\nUse ARM templates.")
    
    write_markdown(root / "deployment" / "onprem.md", 
                  title="On-Premises Deployment",
                  content="Instructions for on-premises deployment.\n\n## Requirements\n\n- Docker\n- Kubernetes")
    
    write_markdown(root / "basic" / "intro.md",
                  title="Introduction", 
                  content="Basic introduction to the project.")
    
    return root


# ====================== Хелперы для глобов ======================

def create_glob_test_files(root: Path) -> None:
    """Создает набор файлов для тестирования глобов."""
    
    # Создаем несколько файлов в docs/
    write_markdown(root / "docs" / "overview.md",
                  title="Overview", 
                  content="Project overview")
    
    write_markdown(root / "docs" / "tutorial.md",
                  title="Tutorial",
                  content="Step by step tutorial")
    
    write_markdown(root / "docs" / "faq.md",
                  title="FAQ", 
                  content="Frequently asked questions")
    
    # Создаем файлы в подпапках
    write_markdown(root / "docs" / "advanced" / "internals.md",
                  title="Internals",
                  content="Internal architecture")
    
    write_markdown(root / "docs" / "advanced" / "plugins.md", 
                  title="Plugins",
                  content="Plugin development")


# ====================== Экспорты ======================

__all__ = [
    # Основные фикстуры
    "md_project", "federated_md_project", "adaptive_md_project",
    
    # Хелперы для создания файлов  
    "write", "write_markdown", "create_basic_lg_cfg", "create_template",
    
    # Хелперы для рендеринга
    "render_template", "make_run_options",
    
    # Хелперы для глобов
    "create_glob_test_files"
]