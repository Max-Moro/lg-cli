"""
Билдеры для создания различных типов тестовых проектов.

Объединяет логику создания проектов из всех conftest.py файлов.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

from .file_utils import write, write_source_file, write_markdown
from .config_builders import (
    create_sections_yaml, create_modes_yaml, create_tags_yaml, 
    get_basic_sections_config, get_multilang_sections_config
)


# ===== Configuration Classes =====

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


# ===== Project Builders =====

class ProjectBuilder:
    """Базовый билдер проектов с fluent API."""
    
    def __init__(self, root: Path):
        self.root = root
        self._sections_config: Optional[Dict[str, Dict[str, Any]]] = None
        self._modes_config: Optional[Dict[str, ModeSetConfig]] = None
        self._tags_config: Optional[tuple] = None
        self._files: List[tuple] = []  # (path, content, file_type)
        
    def with_sections(self, sections_config: Dict[str, Dict[str, Any]]) -> 'ProjectBuilder':
        """Добавляет конфигурацию секций."""
        self._sections_config = sections_config
        return self
        
    def with_basic_sections(self) -> 'ProjectBuilder':
        """Добавляет базовую конфигурацию секций."""
        return self.with_sections(get_basic_sections_config())
        
    def with_multilang_sections(self) -> 'ProjectBuilder':
        """Добавляет многоязычную конфигурацию секций."""
        return self.with_sections(get_multilang_sections_config())
        
    def with_modes(self, modes_config: Dict[str, ModeSetConfig]) -> 'ProjectBuilder':
        """Добавляет конфигурацию режимов."""
        self._modes_config = modes_config
        return self
        
    def with_tags(self, tag_sets: Dict[str, TagSetConfig], global_tags: Dict[str, TagConfig]) -> 'ProjectBuilder':
        """Добавляет конфигурацию тегов."""
        self._tags_config = (tag_sets, global_tags)
        return self
        
    def with_file(self, path: str, content: str, file_type: str = "text") -> 'ProjectBuilder':
        """Добавляет файл в проект."""
        self._files.append((path, content, file_type))
        return self
        
    def with_source_file(self, path: str, content: str, language: str = "python") -> 'ProjectBuilder':
        """Добавляет исходный файл."""
        return self.with_file(path, content, f"source:{language}")
        
    def with_markdown_file(self, path: str, title: str = "", content: str = "") -> 'ProjectBuilder':
        """Добавляет markdown файл."""
        return self.with_file(path, f"{title}|||{content}", "markdown")
        
    def build(self) -> Path:
        """Строит проект и возвращает корневую директорию."""
        # Создаем конфигурацию
        if self._sections_config:
            create_sections_yaml(self.root, self._sections_config)
            
        if self._modes_config:
            create_modes_yaml(self.root, self._modes_config)
            
        if self._tags_config:
            tag_sets, global_tags = self._tags_config
            create_tags_yaml(self.root, tag_sets, global_tags)
            
        # Создаем файлы
        for path, content, file_type in self._files:
            file_path = self.root / path
            
            if file_type == "text":
                write(file_path, content)
            elif file_type.startswith("source:"):
                language = file_type.split(":", 1)[1]
                write_source_file(file_path, content, language)
            elif file_type == "markdown":
                if "|||" in content:
                    title, content = content.split("|||", 1)
                    write_markdown(file_path, title, content)
                else:
                    write_markdown(file_path, content=content)
            else:
                write(file_path, content)
                
        return self.root


def create_basic_project(root: Path) -> Path:
    """
    Создает базовый проект для тестирования плейсхолдеров секций и шаблонов.
    
    Включает:
    - Стандартные секции (src, docs, all, tests)
    - Несколько исходных файлов разных типов
    - Базовую структуру директорий
    """
    builder = ProjectBuilder(root).with_basic_sections()
    
    # Исходные файлы
    builder.with_source_file("src/main.py", 
                           "def main():\n    print('Hello from main')\n    return 0")
    
    builder.with_source_file("src/utils.py", 
                           "def helper_function(x):\n    return x * 2\n\nclass Helper:\n    pass")
    
    builder.with_source_file("src/config.py", 
                           "CONFIG = {\n    'app_name': 'test',\n    'version': '1.0.0'\n}")
    
    # Документация
    builder.with_markdown_file("docs/README.md", "Project Documentation", 
                             "This is the main project documentation.\n\n## Features\n\n- Feature A: Core functionality\n- Feature B: Additional utilities\n\n## Usage\n\nSee the API reference for details.")
    
    builder.with_markdown_file("docs/api.md", "API Reference",
                             "## Functions\n\n### main()\n\nMain entry point.\n\n### helper_function(x)\n\nHelper utility function.")
    
    # Тестовые файлы
    builder.with_source_file("tests/test_main.py", 
                           "def test_main():\n    assert True\n\ndef test_helper():\n    assert helper_function(2) == 4")
    
    return builder.build()


def create_multilang_project(root: Path) -> Path:
    """
    Создает многоязычный проект для тестирования сложных конфигураций.
    
    Включает:
    - Файлы Python и TypeScript
    - Специализированные секции для разных языков
    - Shared документацию
    """
    builder = ProjectBuilder(root).with_multilang_sections()
    
    # Python файлы
    builder.with_source_file("python/__init__.py", "", "python")
    builder.with_source_file("python/core.py", 
                           "class Core:\n    def process(self):\n        pass", "python")
    
    # TypeScript файлы
    builder.with_source_file("typescript/app.ts",
                           "export class App {\n  run(): void {\n    console.log('Running');\n  }\n}", "typescript")
    
    builder.with_source_file("typescript/utils.tsx",
                           "import React from 'react';\n\nexport const Component = () => <div>Hello</div>;", "typescript")
    
    # Общая документация
    builder.with_markdown_file("shared-docs/architecture.md", "Architecture Overview",
                             "This project uses a multilingual approach:\n\n## Backend (Python)\n\nCore business logic implementation.\n\n## Frontend (TypeScript)\n\nUser interface and interaction layer.")
    
    return builder.build()


def create_federated_project(root: Path) -> Path:
    """
    Создает федеративный проект (монорепо) для тестирования адресных ссылок.
    """
    # Корневые секции
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
    
    builder = ProjectBuilder(root).with_sections(root_sections)
    
    # Корневые файлы
    builder.with_markdown_file("README.md", "Federated Project",
                             "This is a monorepo with multiple modules.\n\n## Structure\n\n- apps/web - Web application\n- libs/core - Core library")
    
    builder.with_markdown_file("docs/overview.md", "Project Overview", "Comprehensive project documentation.")
    
    # Создаем базовый проект
    builder.build()
    
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
    
    write_markdown(root / "apps" / "web" / "docs" / "deployment.md", "Web App Deployment",
                  "Deployment instructions for the web application.")
    
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


def create_adaptive_project(root: Path) -> Path:
    """
    Создает базовый проект с адаптивными возможностями.
    
    Включает:
    - Стандартные режимы и теги
    - Базовые секции
    - Несколько исходных файлов для тестирования
    """
    # Создаем конфигурацию режимов
    mode_sets = get_default_modes_config()
    create_modes_yaml(root, mode_sets)
    
    # Создаем конфигурацию тегов
    tag_sets, global_tags = get_default_tags_config()
    create_tags_yaml(root, tag_sets, global_tags)
    
    # Создаем базовые секции
    create_sections_yaml(root, get_basic_sections_config())
    
    # Создаем тестовые файлы
    builder = ProjectBuilder(root)
    builder.with_source_file("src/main.py", "def main():\n    print('Hello, world!')\n")
    builder.with_source_file("src/utils.py", "def helper():\n    return 42\n")
    builder.with_markdown_file("docs/README.md", "Project Documentation", "This is a test project.")
    builder.with_source_file("tests/test_main.py", "def test_main():\n    assert True\n")
    
    # Bilid без конфигурации (уже создали выше)
    builder._sections_config = None
    builder.build()
    
    return root


def create_md_project(root: Path) -> Path:
    """
    Создает базовый проект для тестирования md-плейсхолдеров.
    
    Включает:
    - Минимальную конфигурацию lg-cfg
    - Несколько тестовых Markdown-файлов
    - Базовую структуру директорий
    """
    from .config_builders import create_basic_lg_cfg
    
    # Создаем базовую конфигурацию
    create_basic_lg_cfg(root)
    
    builder = ProjectBuilder(root)
    
    # Создаем тестовые Markdown-файлы
    builder.with_markdown_file("README.md", "Main Project", 
                             "This is the main project documentation.\n\n## Features\n\n- Feature A\n- Feature B")
    
    builder.with_markdown_file("docs/guide.md", "User Guide", 
                             "This is a comprehensive user guide.\n\n## Installation\n\nRun the installer.\n\n## Usage\n\nUse the app.")
    
    builder.with_markdown_file("docs/api.md", "API Reference", 
                             "API documentation.\n\n## Authentication\n\nUse API keys.\n\n## Endpoints\n\n### GET /users\n\nGet users list.")
    
    # Файл без H1 для тестов strip_h1
    builder.with_file("docs/changelog.md", "## v1.0.0\n\n- Initial release\n\n## v0.9.0\n\n- Beta version")
    
    # Файл в lg-cfg для тестов @self:
    builder.with_markdown_file("lg-cfg/internal.md", "Internal Documentation",
                             "This is internal documentation stored in lg-cfg.")
    
    builder._sections_config = None  # Уже создали выше
    return builder.build()


__all__ = [
    # Configuration classes
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
    
    # Builder classes
    "ProjectBuilder",
    
    # Project builders
    "create_basic_project", "create_multilang_project", "create_federated_project",
    "create_adaptive_project", "create_md_project",
    
    # Default configurations
    "get_default_modes_config", "get_default_tags_config"
]