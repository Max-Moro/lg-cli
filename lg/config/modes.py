"""
Modes configuration loader.
Supports federated configuration with child scope inclusions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from ruamel.yaml import YAML

from lg.migrate import ensure_cfg_actual
from .adaptive_model import ModesConfig, ModeSet, DEFAULT_MODES_CONFIG
from .mode_sets_list_schema import ModeSetsList, ModeSet as ModeSetSchema, Mode as ModeSchema
from .paths import (
    cfg_root,
    modes_path,
)

_yaml = YAML(typ="safe")


def _read_yaml_map(path: Path) -> dict:
    """Reads a YAML file and returns a dictionary."""
    if not path.is_file():
        return {}
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _load_modes_from_path(path: Path) -> ModesConfig:
    """Loads modes from a single modes.yaml file."""
    raw = _read_yaml_map(path)
    return ModesConfig.from_dict(raw)


def _merge_mode_sets(parent: Dict[str, ModeSet], child: Dict[str, ModeSet]) -> Dict[str, ModeSet]:
    """
    Merges mode sets with parent configuration priority.

    Merge rules:
    - If a mode set with the same name exists in both parent and child scopes,
      the parent configuration has priority
    - Individual modes within a set are merged, with parent modes taking priority
    """
    result = dict(child)  # Start with child modes

    for name, parent_mode_set in parent.items():
        if name in result:
            # Set exists in both configurations - merge modes
            child_mode_set = result[name]
            merged_modes = dict(child_mode_set.modes)
            merged_modes.update(parent_mode_set.modes)  # Parent modes override child

            result[name] = ModeSet(
                title=parent_mode_set.title,  # Parent title takes priority
                modes=merged_modes
            )
        else:
            # Set only in parent configuration
            result[name] = parent_mode_set

    return result


def load_modes(root: Path) -> ModesConfig:
    """
    Loads modes configuration with support for federated structure.

    Args:
        root: Repository root

    Returns:
        Merged modes configuration
    """
    base = cfg_root(root)
    if not base.is_dir():
        return DEFAULT_MODES_CONFIG

    # Update lg-cfg/ to actual format
    ensure_cfg_actual(base)

    # Load main configuration
    modes_file = modes_path(root)
    if not modes_file.is_file():
        return DEFAULT_MODES_CONFIG

    config = _load_modes_from_path(modes_file)

    # Process child scope inclusions
    for child_scope in config.include:
        child_root = (root / child_scope).resolve()
        if not child_root.is_dir():
            continue

        child_cfg_root = cfg_root(child_root)
        if not child_cfg_root.is_dir():
            continue

        child_modes_file = modes_path(child_root)
        if not child_modes_file.is_file():
            continue

        try:
            child_config = _load_modes_from_path(child_modes_file)
            # Merge mode sets
            config.mode_sets = _merge_mode_sets(config.mode_sets, child_config.mode_sets)
        except Exception as e:
            # Log error but don't interrupt loading
            import logging
            logging.warning(f"Failed to load child modes from {child_scope}: {e}")

    return config


def list_mode_sets(root: Path) -> ModeSetsList:
    """
    Returns a typed object with a list of mode sets for CLI command 'list mode-sets'.

    Returns:
        ModeSetsList: Typed object with an array of mode sets
    """
    config = load_modes(root)
    mode_sets_list = []
    
    for mode_set_id, mode_set in config.mode_sets.items():
        modes_list = []
        for mode_id, mode in mode_set.modes.items():
            mode_schema = ModeSchema(
                id=mode_id,
                title=mode.title,
                description=mode.description if mode.description else None,
                tags=list(mode.tags) if mode.tags else None,
                options=dict(mode.options) if mode.options else None
            )
            modes_list.append(mode_schema)
        
        mode_set_schema = ModeSetSchema(
            id=mode_set_id,
            title=mode_set.title,
            modes=modes_list
        )
        mode_sets_list.append(mode_set_schema)

    # Sort by id for stable order
    mode_sets_list.sort(key=lambda x: x.id)

    return ModeSetsList(**{"mode-sets": mode_sets_list})