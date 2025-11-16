"""
Mapping of file names and extensions to languages for markdown fencing.
Extended as needed.
"""

from pathlib import Path
from typing import Final

from ..types import LangName

# Main dictionary: name (lowercase) or extension → fence language
LANG_MAPPING: Final[dict[str, str]] = {
    # Extensions
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".md": "markdown",
    ".markdown": "markdown",
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

    # Special file names
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
    "README": "",        # without extension
}

def get_language_for_file(path: Path) -> LangName:
    """
    Returns the language for fenced code based on file name or extension.
    First, tries exact name match (case-insensitive), then suffix.lower().
    By default, returns an empty string (no language specified).
    """
    name = path.name
    # Exact name match (case-insensitive)
    lang = LANG_MAPPING.get(name) or LANG_MAPPING.get(name.lower())
    if lang is not None:
        return lang
    # By extension
    return LANG_MAPPING.get(path.suffix.lower(), "")
