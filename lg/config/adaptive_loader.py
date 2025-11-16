"""
Utilities for working with modes and tags in the adaptive system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Tuple, Optional

from .modes import load_modes, ModesConfig
from .tags import load_tags, TagsConfig, TagSet, Tag
from .adaptive_model import ModeOptions


class AdaptiveConfigLoader:
    """
    Centralized loader for modes and tags configuration with caching.
    Avoids repeated loading of the same YAML files.
    """

    def __init__(self, root: Path):
        self.root = root
        self._modes_config: Optional[ModesConfig] = None
        self._tags_config: Optional[TagsConfig] = None

    def get_modes_config(self) -> ModesConfig:
        """Load modes configuration with caching."""
        if self._modes_config is None:
            self._modes_config = load_modes(self.root)
        return self._modes_config

    def get_tags_config(self) -> TagsConfig:
        """Load tags configuration with caching."""
        if self._tags_config is None:
            self._tags_config = load_tags(self.root)
        return self._tags_config

    def get_all_available_tags(self) -> Tuple[Dict[str, TagSet], Dict[str, Tag]]:
        """Return all available tags, separated into sets and global."""
        config = self.get_tags_config()
        return config.tag_sets, config.global_tags


def process_adaptive_options(
    root: Path,
    modes: Dict[str, str],
    extra_tags: Set[str]
) -> Tuple[Set[str], ModeOptions, AdaptiveConfigLoader]:
    """
    Main function for processing adaptive options.
    Validates modes and tags, computes active tags and merges mode options.

    Args:
        root: Repository root
        modes: Dictionary of active modes {modeset_name: mode_name}
        extra_tags: Additional explicitly specified tags

    Returns:
        Tuple (active_tags, merged_mode_options, config_loader)

    Raises:
        ValueError: If mode or mode set not found
    """
    loader = AdaptiveConfigLoader(root)

    # Validate modes
    if modes:
        _validate_modes_with_config(loader.get_modes_config(), modes)

    # Validate tags
    if extra_tags:
        _validate_tags_with_config(loader.get_all_available_tags(), extra_tags)

    # Compute active tags
    active_tags = _compute_active_tags_with_config(
        loader.get_modes_config(),
        modes,
        extra_tags
    )

    # Merge options from all active modes
    mode_options = ModeOptions.merge_from_modes(
        loader.get_modes_config(),
        modes
    )

    return active_tags, mode_options, loader


def _validate_modes_with_config(modes_config: ModesConfig, modes: Dict[str, str]) -> None:
    """
    Validate specified modes using already loaded configuration.

    Args:
        modes_config: Loaded modes configuration
        modes: Dictionary of modes to validate

    Raises:
        ValueError: If mode or mode set not found
    """
    for modeset_name, mode_name in modes.items():
        modeset = modes_config.mode_sets.get(modeset_name)
        if not modeset:
            available_modesets = list(modes_config.mode_sets.keys())
            raise ValueError(
                f"Unknown mode set '{modeset_name}'. "
                f"Available mode sets: {', '.join(available_modesets)}"
            )

        if mode_name not in modeset.modes:
            available_modes = list(modeset.modes.keys())
            raise ValueError(
                f"Unknown mode '{mode_name}' in mode set '{modeset_name}'. "
                f"Available modes: {', '.join(available_modes)}"
            )


def _validate_tags_with_config(all_tags: Tuple[Dict[str, TagSet], Dict[str, Tag]], tags: Set[str]) -> None:
    """
    Validate specified tags using already loaded configuration.
    Outputs warnings for unknown tags.

    Args:
        all_tags: Tuple (tag_sets, global_tags)
        tags: Set of tags to validate
    """
    if not tags:
        return

    tag_sets, global_tags = all_tags

    # Collect all known tags
    all_known_tags = set(global_tags.keys())
    for tag_set in tag_sets.values():
        all_known_tags.update(tag_set.tags.keys())

    # Check for unknown tags
    unknown_tags = tags - all_known_tags
    if unknown_tags:
        import logging
        logging.warning(
            f"Unknown tags: {', '.join(sorted(unknown_tags))}. "
            f"They will be processed but may not affect the output."
        )


def _compute_active_tags_with_config(
    modes_config: ModesConfig,
    modes: Dict[str, str],
    extra_tags: Set[str]
) -> Set[str]:
    """
    Compute set of active tags using already loaded configuration.

    Args:
        modes_config: Loaded modes configuration
        modes: Dictionary of active modes {modeset_name: mode_name}
        extra_tags: Additional explicitly specified tags

    Returns:
        Set of all active tags
    """
    active_tags = set(extra_tags)  # Start with explicitly specified tags

    # Collect tags from active modes
    for modeset_name, mode_name in modes.items():
        modeset = modes_config.mode_sets.get(modeset_name)
        if not modeset:
            # Unknown mode set - skip (already checked in validation)
            continue

        mode = modeset.modes.get(mode_name)
        if not mode:
            # Unknown mode - skip (already checked in validation)
            continue

        # Add mode tags
        active_tags.update(mode.tags)

    return active_tags
