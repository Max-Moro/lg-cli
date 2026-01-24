"""
Section extractor for the adaptive system.

Extracts AdaptiveModel from SectionCfg raw dictionaries.
"""

from __future__ import annotations

from typing import Dict, Any

from .model import AdaptiveModel, ModeSet, TagSet
from ..section.model import SectionCfg


def extract_adaptive_model(section_cfg: SectionCfg) -> AdaptiveModel:
    """
    Extract AdaptiveModel from section configuration.

    Parses mode_sets_raw and tag_sets_raw dictionaries into
    typed ModeSet and TagSet objects.

    Args:
        section_cfg: Section configuration with raw adaptive data

    Returns:
        AdaptiveModel with parsed mode-sets and tag-sets
    """
    mode_sets: Dict[str, ModeSet] = {}
    tag_sets: Dict[str, TagSet] = {}

    # Parse mode-sets
    for set_id, set_data in section_cfg.mode_sets_raw.items():
        if isinstance(set_data, dict):
            mode_sets[set_id] = ModeSet.from_dict(set_id, set_data)

    # Parse tag-sets
    for set_id, set_data in section_cfg.tag_sets_raw.items():
        if isinstance(set_data, dict):
            tag_sets[set_id] = TagSet.from_dict(set_id, set_data)

    return AdaptiveModel(mode_sets=mode_sets, tag_sets=tag_sets)


__all__ = ["extract_adaptive_model"]
