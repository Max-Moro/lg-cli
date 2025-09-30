"""
Утилиты для создания файлов и директорий в тестах.

Унифицирует все file-related функции, которые дублировались 
в различных conftest.py файлах.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional


def write(p: Path, text: str) -> Path:
    """
    Записывает текст в файл, создавая родительские директории при необходимости.
    
    Базовая функция для всех file operations. Заменяет дублированные write() 
    функции из различных conftest.py.
    
    Args:
        p: Путь к файлу
        text: Содержимое для записи
        
    Returns:
        Путь к созданному файлу
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_source_file(p: Path, content: str, language: str = "python") -> Path:
    """
    Создает исходный файл с содержимым для конкретного языка.
    
    Добавляет комментарий с именем файла и обрабатывает содержимое.
    
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
        "cpp": "// ",
        "c": "// ",
        "scala": "// "
    }
    
    comment_prefix = comment_map.get(language, "# ")
    
    lines = [f"{comment_prefix}Source file: {p.name}", ""]
    
    if content:
        lines.append(content.strip())
    
    return write(p, "\n".join(lines) + "\n")


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


# Удалены дублирующие функции create_temp_file и write_text_file
# Используйте write() напрямую


__all__ = [
    "write", "write_source_file", "write_markdown"
]