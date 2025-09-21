"""
Загрузчик конфигурации тегов.
Поддерживает федеративную конфигурацию с включением дочерних скоупов.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from ruamel.yaml import YAML

from lg.migrate import ensure_cfg_actual
from .adaptive_model import TagsConfig, TagSet, Tag, DEFAULT_TAGS_CONFIG
from .paths import (
    cfg_root,
    tags_path,
)
from .tag_sets_list_schema import TagSetsList, TagSet as TagSetSchema, Tag as TagSchema

_yaml = YAML(typ="safe")


def _read_yaml_map(path: Path) -> dict:
    """Читает YAML файл и возвращает словарь."""
    if not path.is_file():
        return {}
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _load_tags_from_path(path: Path) -> TagsConfig:
    """Загружает теги из одного файла tags.yaml."""
    raw = _read_yaml_map(path)
    return TagsConfig.from_dict(raw)


def _merge_tag_sets(parent: Dict[str, TagSet], child: Dict[str, TagSet]) -> Dict[str, TagSet]:
    """
    Объединяет наборы тегов с приоритетом родительской конфигурации.
    
    Правила объединения:
    - Наборы тегов с одинаковыми именами объединяются
    - Теги с одинаковыми именами в одном наборе используют определение из родительского скоупа
    """
    result = dict(child)  # Начинаем с дочерних наборов
    
    for name, parent_tag_set in parent.items():
        if name in result:
            # Набор существует в обеих конфигурациях - объединяем теги
            child_tag_set = result[name]
            merged_tags = dict(child_tag_set.tags)
            merged_tags.update(parent_tag_set.tags)  # Родительские перезаписывают дочерние
            
            result[name] = TagSet(
                title=parent_tag_set.title,  # Приоритет родительского title
                tags=merged_tags
            )
        else:
            # Набор только в родительской конфигурации
            result[name] = parent_tag_set
    
    return result


def _merge_global_tags(parent: Dict[str, Tag], child: Dict[str, Tag]) -> Dict[str, Tag]:
    """
    Объединяет глобальные теги с приоритетом родительской конфигурации.
    """
    result = dict(child)  # Начинаем с дочерних тегов
    result.update(parent)  # Родительские перезаписывают дочерние
    return result


def load_tags(root: Path) -> TagsConfig:
    """
    Загружает конфигурацию тегов с поддержкой федеративной структуры.
    
    Args:
        root: Корень репозитория
        
    Returns:
        Объединенная конфигурация тегов
    """
    base = cfg_root(root)
    if not base.is_dir():
        return DEFAULT_TAGS_CONFIG
    
    # Приводим lg-cfg/ к актуальному формату
    ensure_cfg_actual(base)
    
    # Загружаем основную конфигурацию
    tags_file = tags_path(root)
    if not tags_file.is_file():
        return DEFAULT_TAGS_CONFIG
    
    config = _load_tags_from_path(tags_file)
    
    # Обрабатываем включения дочерних скоупов
    for child_scope in config.include:
        child_root = (root / child_scope).resolve()
        if not child_root.is_dir():
            continue
        
        child_cfg_root = cfg_root(child_root)
        if not child_cfg_root.is_dir():
            continue
        
        child_tags_file = tags_path(child_root)
        if not child_tags_file.is_file():
            continue
        
        try:
            child_config = _load_tags_from_path(child_tags_file)
            # Объединяем наборы тегов и глобальные теги
            config.tag_sets = _merge_tag_sets(config.tag_sets, child_config.tag_sets)
            config.global_tags = _merge_global_tags(config.global_tags, child_config.global_tags)
        except Exception as e:
            # Логируем ошибку, но не прерываем загрузку
            import logging
            logging.warning(f"Failed to load child tags from {child_scope}: {e}")
    
    return config


def list_tag_sets(root: Path) -> TagSetsList:
    """
    Возвращает типизированный объект со списком наборов тегов для CLI команды 'lg list tag-sets'.
    
    Returns:
        TagSetsList: Типизированный объект с массивом наборов тегов
    """
    config = load_tags(root)
    tag_sets_list = []
    
    # Наборы тегов
    for tag_set_id, tag_set in config.tag_sets.items():
        tags_list = []
        for tag_id, tag in tag_set.tags.items():
            tag_schema = TagSchema(
                id=tag_id,
                title=tag.title,
                description=tag.description if tag.description else None
            )
            tags_list.append(tag_schema)
        
        tag_set_schema = TagSetSchema(
            id=tag_set_id,
            title=tag_set.title,
            tags=tags_list
        )
        tag_sets_list.append(tag_set_schema)
    
    # Глобальные теги (если есть)
    if config.global_tags:
        global_tags_list = []
        for tag_id, tag in config.global_tags.items():
            tag_schema = TagSchema(
                id=tag_id,
                title=tag.title,
                description=tag.description if tag.description else None
            )
            global_tags_list.append(tag_schema)
        
        global_tag_set_schema = TagSetSchema(
            id="global",
            title="Глобальные теги",
            tags=global_tags_list
        )
        tag_sets_list.append(global_tag_set_schema)
    
    # Сортируем по id для стабильного порядка
    tag_sets_list.sort(key=lambda x: x.id)
    
    return TagSetsList(**{"tag-sets": tag_sets_list})
