"""
Фикстуры для тестов task_placeholder.
"""

from pathlib import Path

import pytest

from tests.infrastructure import write, create_basic_sections_yaml


@pytest.fixture
def task_project(tmp_path: Path):
    """
    Минимальный проект с конфигурацией для тестирования task-плейсхолдеров.
    """
    root = tmp_path
    
    # Создаем базовую конфигурацию секций
    create_basic_sections_yaml(root)
    
    # Создаем простые файлы для секций
    write(root / "src" / "main.py", "def main():\n    pass\n")
    write(root / "docs" / "README.md", "# Project\n\nDocumentation here.\n")
    
    return root


@pytest.fixture
def task_text_simple():
    """Простой текст задачи для тестов."""
    return "Implement caching for API responses"


@pytest.fixture
def task_text_multiline():
    """Многострочный текст задачи."""
    return """Refactoring tasks:
- Extract common utilities
- Add type hints
- Improve error handling"""


@pytest.fixture
def task_text_with_quotes():
    """Текст задачи с кавычками для проверки экранирования."""
    return 'Fix "critical" bug in authentication'
