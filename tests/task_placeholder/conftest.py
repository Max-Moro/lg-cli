"""
Fixtures for task_placeholder tests.
"""

from pathlib import Path

import pytest

from tests.infrastructure import write, create_basic_sections_yaml


@pytest.fixture
def task_project(tmp_path: Path):
    """
    Minimal project with configuration for testing task placeholders.
    """
    root = tmp_path

    # Create basic sections configuration
    create_basic_sections_yaml(root)

    # Create simple files for sections
    write(root / "src" / "main.py", "def main():\n    pass\n")
    write(root / "docs" / "README.md", "# Project\n\nDocumentation here.\n")

    return root


@pytest.fixture
def task_text_simple():
    """Simple task text for tests."""
    return "Implement caching for API responses"


@pytest.fixture
def task_text_multiline():
    """Multiline task text."""
    return """Refactoring tasks:
- Extract common utilities
- Add type hints
- Improve error handling"""


@pytest.fixture
def task_text_with_quotes():
    """Task text with quotes to check escaping."""
    return 'Fix "critical" bug in authentication'
