"""
Mapping of file names and extensions to languages for markdown fencing.
Дополняется по мере надобности.
"""

from pathlib import Path
from typing import Final

from ..types import LangName

# Основной словарь: name (lowercase) или extension → fence language
LANG_MAPPING: Final[dict[str, str]] = {
    # Расширения
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".md": "",
    ".markdown": "",
    ".txt": "",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".ini": "",
    ".cfg": "",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".sql": "sql",

    # Специальные имена
    "pyproject.toml": "toml",
    "Pipfile": "",
    "pom.xml": "xml",
    "build.gradle": "groovy",
    "build.gradle.kts": "kotlin",
    "package.json": "json",
    "tsconfig.json": "json",
    "webpack.config.js": "javascript",
    "Dockerfile": "dockerfile",
    "Makefile": "make",
    "README": "",        # без расширения
}

def get_language_for_file(path: Path) -> LangName:
    """
    Возвращает язык для fenced-кода по имени файла или расширению.
    Сначала пробуем полное имя (без учёта регистра), затем suffix.lower().
    По умолчанию — пустая строка (без указания языка).
    """
    name = path.name
    # точное совпадение имени (без регистра)
    lang = LANG_MAPPING.get(name) or LANG_MAPPING.get(name.lower())
    if lang is not None:
        return lang
    # по расширению
    return LANG_MAPPING.get(path.suffix.lower(), "")
