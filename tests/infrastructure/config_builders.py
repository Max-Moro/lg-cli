"""
Билдеры для создания конфигурационных YAML файлов в тестах.

Унифицирует создание sections.yaml, modes.yaml, tags.yaml и других конфигов.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Any

from ruamel.yaml import YAML

from .file_utils import write


def create_sections_yaml(root: Path, sections_config: Dict[str, Dict[str, Any]]) -> Path:
    """
    Создает lg-cfg/sections.yaml с указанными секциями.
    
    Args:
        root: Корень проекта
        sections_config: Словарь конфигурации секций
        
    Returns:
        Путь к созданному файлу
    """
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
    fragment_file = root / "lg-cfg" / f"{fragment_path}.sec.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    fragment_file.parent.mkdir(parents=True, exist_ok=True)
    with fragment_file.open("w", encoding="utf-8") as f:
        yaml.dump(sections_config, f)
    
    return fragment_file


def create_modes_yaml(
    root: Path, 
    mode_sets: Optional[Dict[str, Any]] = None,
    include: Optional[List[str]] = None, 
    append: bool = False
) -> Path:
    """
    Создает файл modes.yaml с указанными наборами режимов.
    
    Args:
        root: Корень проекта
        mode_sets: Словарь наборов режимов (может быть ModeSetConfig или dict)
        include: Список дочерних скоупов для включения
        append: Если True, дополняет существующую конфигурацию
        
    Returns:
        Путь к созданному файлу
    """
    modes_file = root / "lg-cfg" / "modes.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    # Загружаем существующую конфигурацию если append=True
    existing_data = {}
    if append and modes_file.exists():
        with modes_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}
    
    new_data = {}
    
    if mode_sets:
        # Поддерживаем как plain dict, так и структурированные объекты
        if isinstance(list(mode_sets.values())[0], dict):
            new_data["mode-sets"] = mode_sets
        else:
            # Конвертируем из ModeSetConfig в dict (если нужно)
            new_mode_sets = {}
            for set_name, mode_set in mode_sets.items():
                if hasattr(mode_set, 'modes'):  # ModeSetConfig
                    modes_dict = {}
                    for mode_name, mode in mode_set.modes.items():
                        mode_dict = {"title": mode.title}
                        if hasattr(mode, 'description') and mode.description:
                            mode_dict["description"] = mode.description
                        if hasattr(mode, 'tags') and mode.tags:
                            mode_dict["tags"] = mode.tags
                        if hasattr(mode, 'options'):
                            mode_dict.update(mode.options)
                        modes_dict[mode_name] = mode_dict
                    
                    new_mode_sets[set_name] = {
                        "title": mode_set.title,
                        "modes": modes_dict
                    }
                else:
                    new_mode_sets[set_name] = mode_set
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


def create_tags_yaml(
    root: Path, 
    tag_sets: Optional[Dict[str, Any]] = None,
    global_tags: Optional[Dict[str, Any]] = None, 
    include: Optional[List[str]] = None,
    append: bool = False
) -> Path:
    """
    Создает файл tags.yaml с указанными наборами тегов.
    
    Args:
        root: Корень проекта
        tag_sets: Словарь наборов тегов (может быть TagSetConfig или dict)
        global_tags: Словарь глобальных тегов (может быть TagConfig или dict)
        include: Список дочерних скоупов для включения
        append: Если True, дополняет существующую конфигурацию
        
    Returns:
        Путь к созданному файлу
    """
    tags_file = root / "lg-cfg" / "tags.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    
    # Загружаем существующую конфигурацию если append=True
    existing_data = {}
    if append and tags_file.exists():
        with tags_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}
    
    new_data = {}
    
    if tag_sets:
        # Поддерживаем как plain dict, так и структурированные объекты  
        if isinstance(list(tag_sets.values())[0], dict):
            new_data["tag-sets"] = tag_sets
        else:
            # Конвертируем из TagSetConfig в dict
            new_tag_sets = {}
            for set_name, tag_set in tag_sets.items():
                if hasattr(tag_set, 'tags'):  # TagSetConfig
                    tags_dict = {}
                    for tag_name, tag in tag_set.tags.items():
                        tag_dict = {"title": tag.title}
                        if hasattr(tag, 'description') and tag.description:
                            tag_dict["description"] = tag.description
                        tags_dict[tag_name] = tag_dict
                    
                    new_tag_sets[set_name] = {
                        "title": tag_set.title,
                        "tags": tags_dict
                    }
                else:
                    new_tag_sets[set_name] = tag_set
            new_data["tag-sets"] = new_tag_sets
    
    if global_tags:
        # Поддерживаем как plain dict, так и TagConfig объекты
        if isinstance(list(global_tags.values())[0], dict):
            new_data["tags"] = global_tags  
        else:
            # Конвертируем из TagConfig в dict
            new_global_tags = {}
            for tag_name, tag in global_tags.items():
                if hasattr(tag, 'title'):  # TagConfig
                    tag_dict = {"title": tag.title}
                    if hasattr(tag, 'description') and tag.description:
                        tag_dict["description"] = tag.description
                    new_global_tags[tag_name] = tag_dict
                else:
                    new_global_tags[tag_name] = tag
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


def create_basic_lg_cfg(root: Path) -> Path:
    """Создает минимальную конфигурацию lg-cfg/sections.yaml."""
    content = textwrap.dedent("""
    all:
      extensions: [".md"]
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


def create_basic_sections_yaml(root: Path) -> Path:
    """Создает базовый sections.yaml для тестов (из adaptive тестов)."""
    content = textwrap.dedent("""
    src:
      extensions: [".py", ".md"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    
    docs:
      extensions: [".md"]
      markdown:
        max_heading_level: 2
      filters:
        mode: allow  
        allow:
          - "/docs/**"
    
    tests:
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/tests/**"
    """).strip() + "\n"
    
    return write(root / "lg-cfg" / "sections.yaml", content)


# Готовые конфигурации секций
def get_basic_sections_config() -> Dict[str, Dict[str, Any]]:
    """Возвращает базовую конфигурацию секций для тестов."""
    return {
        "src": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        },
        "docs": {
            "extensions": [".md"],
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
            "filters": {
                "mode": "allow",
                "allow": ["/**"]
            }
        },
        "tests": {
            "extensions": [".py"],
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
            "filters": {
                "mode": "allow",
                "allow": ["/typescript/**"]
            }
        },
        "shared-docs": {
            "extensions": [".md"],
            "markdown": {
                "max_heading_level": 3
            },
            "filters": {
                "mode": "allow",
                "allow": ["/shared-docs/**"]
            }
        }
    }


__all__ = [
    # YAML builders (все поддерживают классы конфигурации)
    "create_sections_yaml", "create_section_fragment", "create_modes_yaml", "create_tags_yaml",
    
    # Simple builders
    "create_basic_lg_cfg", "create_basic_sections_yaml", "create_template",
    
    # Predefined configs
    "get_basic_sections_config", "get_multilang_sections_config"
]