from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from .paths import (
    iter_sections_yaml_files,
    iter_section_fragments,
    sections_yaml_prefix,
    canonical_fragment_prefix,
)

_yaml = YAML(typ="safe")


@dataclass(frozen=True)
class SectionLocation:
    """Physical location of a section in configuration files."""
    file_path: Path      # e.g., lg-cfg/adapters/sections.yaml
    local_name: str      # e.g., "src" (key name in YAML)


@dataclass
class ScopeIndex:
    """Index of one scope (one lg-cfg/ directory)."""

    # Full section name → location
    # Keys are unique; collisions resolved during index building
    sections: Dict[str, SectionLocation] = field(default_factory=dict)

    # For cache invalidation: file path → mtime
    file_mtimes: Dict[Path, float] = field(default_factory=dict)


def _read_yaml_top_level_keys(path: Path) -> List[str]:
    """Read only top-level keys from YAML file without full parsing."""
    try:
        raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            return []
        return list(raw.keys())
    except Exception:
        return []


def build_index(cfg_root_path: Path) -> ScopeIndex:
    """
    Build section index for a scope.

    Args:
        cfg_root_path: Path to lg-cfg/ directory

    Returns:
        ScopeIndex with all sections mapped
    """
    sections: Dict[str, SectionLocation] = {}
    file_mtimes: Dict[Path, float] = {}

    # Get repository root (parent of lg-cfg/)
    root = cfg_root_path.parent

    # Step 1: Process sections.yaml files (priority)
    for sections_file in iter_sections_yaml_files(root):
        try:
            file_mtimes[sections_file] = sections_file.stat().st_mtime
        except Exception:
            continue

        dir_prefix = sections_yaml_prefix(root, sections_file)

        for local_name in _read_yaml_top_level_keys(sections_file):
            full_name = f"{dir_prefix}/{local_name}" if dir_prefix else local_name
            sections[full_name] = SectionLocation(sections_file, local_name)

    # Step 2: Process *.sec.yaml files (don't overwrite existing)
    for sec_file in iter_section_fragments(root):
        try:
            file_mtimes[sec_file] = sec_file.stat().st_mtime
        except Exception:
            continue

        dir_prefix = canonical_fragment_prefix(root, sec_file)
        local_names = _read_yaml_top_level_keys(sec_file)

        for local_name in local_names:
            if len(local_names) == 1:
                # Single section: without file prefix
                # Extract directory prefix (all segments except last)
                prefix_parts = dir_prefix.split("/") if dir_prefix else []
                if len(prefix_parts) > 1:
                    # Has subdirectories - preserve them
                    dir_only_prefix = "/".join(prefix_parts[:-1])
                    full_name = f"{dir_only_prefix}/{local_name}"
                else:
                    # No subdirectories - just section name
                    full_name = local_name
            else:
                # Multiple sections: with file prefix
                full_name = f"{dir_prefix}/{local_name}"

            # Don't overwrite existing (sections.yaml wins)
            if full_name not in sections:
                sections[full_name] = SectionLocation(sec_file, local_name)

    return ScopeIndex(sections=sections, file_mtimes=file_mtimes)


def iter_all_config_files(cfg_root_path: Path) -> List[Path]:
    """Get all configuration files for a scope."""
    root = cfg_root_path.parent
    files = []
    files.extend(iter_sections_yaml_files(root))
    files.extend(iter_section_fragments(root))
    return files


__all__ = ["SectionLocation", "ScopeIndex", "build_index", "iter_all_config_files"]
