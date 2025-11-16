"""
Tags configuration loader.
Supports federated configuration with child scope inclusions.
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
    """Reads a YAML file and returns a dictionary."""
    if not path.is_file():
        return {}
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _load_tags_from_path(path: Path) -> TagsConfig:
    """Loads tags from a single tags.yaml file."""
    raw = _read_yaml_map(path)
    return TagsConfig.from_dict(raw)


def _merge_tag_sets(parent: Dict[str, TagSet], child: Dict[str, TagSet]) -> Dict[str, TagSet]:
    """
    Merges tag sets with parent configuration priority.

    Merge rules:
    - Tag sets with the same names are merged
    - Tags with the same names within a set use the definition from the parent scope
    """
    result = dict(child)  # Start with child sets

    for name, parent_tag_set in parent.items():
        if name in result:
            # Set exists in both configurations - merge tags
            child_tag_set = result[name]
            merged_tags = dict(child_tag_set.tags)
            merged_tags.update(parent_tag_set.tags)  # Parent tags override child

            result[name] = TagSet(
                title=parent_tag_set.title,  # Parent title takes priority
                tags=merged_tags
            )
        else:
            # Set only in parent configuration
            result[name] = parent_tag_set

    return result


def _merge_global_tags(parent: Dict[str, Tag], child: Dict[str, Tag]) -> Dict[str, Tag]:
    """
    Merges global tags with parent configuration priority.
    """
    result = dict(child)  # Start with child tags
    result.update(parent)  # Parent tags override child
    return result


def load_tags(root: Path) -> TagsConfig:
    """
    Loads tags configuration with support for federated structure.

    Args:
        root: Repository root

    Returns:
        Merged tags configuration
    """
    base = cfg_root(root)
    if not base.is_dir():
        return DEFAULT_TAGS_CONFIG

    # Update lg-cfg/ to actual format
    ensure_cfg_actual(base)

    # Load main configuration
    tags_file = tags_path(root)
    if not tags_file.is_file():
        return DEFAULT_TAGS_CONFIG

    config = _load_tags_from_path(tags_file)

    # Process child scope inclusions
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
            # Merge tag sets and global tags
            config.tag_sets = _merge_tag_sets(config.tag_sets, child_config.tag_sets)
            config.global_tags = _merge_global_tags(config.global_tags, child_config.global_tags)
        except Exception as e:
            # Log error but don't interrupt loading
            import logging
            logging.warning(f"Failed to load child tags from {child_scope}: {e}")

    return config


def list_tag_sets(root: Path) -> TagSetsList:
    """
    Returns a typed object with a list of tag sets for CLI command 'lg list tag-sets'.

    Returns:
        TagSetsList: Typed object with an array of tag sets
    """
    config = load_tags(root)
    tag_sets_list = []

    # Tag sets
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

    # Global tags (if any)
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
            title="Global Tags",
            tags=global_tags_list
        )
        tag_sets_list.append(global_tag_set_schema)

    # Sort by id for stable order
    tag_sets_list.sort(key=lambda x: x.id)

    return TagSetsList(**{"tag-sets": tag_sets_list})
