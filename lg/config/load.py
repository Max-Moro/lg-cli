from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ruamel.yaml import YAML

from lg.migrate import ensure_cfg_actual
from .model import Config, SectionCfg
from .paths import (
    cfg_root,
    sections_path,
    iter_section_fragments,
    canonical_fragment_prefix,
)

_yaml = YAML(typ="safe")


def _read_yaml_map(path: Path) -> dict:
    raw = _yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"YAML must be a mapping: {path}")
    return raw


def _collect_sections_from_sections_yaml(root: Path) -> Dict[str, SectionCfg]:
    """
    Read lg-cfg/sections.yaml. All keys are treated as sections with SHORT ids (without path prefix)
    """
    p = sections_path(root)
    if not p.is_file():
        return {}
    raw = _read_yaml_map(p)
    sections: Dict[str, SectionCfg] = {}
    for name, node in raw.items():
        if not isinstance(node, dict):
            raise RuntimeError(f"Section '{name}' in {p} must be a mapping")
        sections[name] = SectionCfg.from_dict(name, node)
    return sections

def _collect_sections_from_fragments(root: Path) -> Dict[str, SectionCfg]:
    """
    Collect sections from all **/*.sec.yaml.
    Canonical section ID is formed as follows:
      • If fragment contains EXACTLY one section → canon-ID = <directory_prefix>/<section_name>.
        File name prefix is dropped, but directory prefix is preserved.
        Example: 'subdir/web.sec.yaml' with single section 'web-api' → 'subdir/web-api'.
      • Otherwise:
          – prefix = file path without '.sec.yaml' suffix relative to lg-cfg/ (POSIX).
          – If last segment of prefix matches section name → canon-ID = prefix
            (eliminates "a/a", "pkg/core/core").
          – Otherwise → canon-ID = 'prefix/<section_local_name>'.
    """
    acc: Dict[str, SectionCfg] = {}
    for frag in iter_section_fragments(root):
        raw = _read_yaml_map(frag)
        prefix = canonical_fragment_prefix(root, frag)

        # Collect list of sections
        section_items = [(name, node) for name, node in raw.items()]
        if not section_items:
            # Empty fragment — valid, but nothing to add
            continue

        # Rule 1: single section → canon = directory_prefix + section_name
        if len(section_items) == 1:
            local_name, node = section_items[0]
            if not isinstance(node, dict):
                raise RuntimeError(f"Section '{local_name}' in {frag} must be a mapping")

            # Extract directory prefix (all segments except last)
            prefix_parts = prefix.split("/") if prefix else []
            if len(prefix_parts) > 1:
                # Has subdirectories - preserve them
                dir_prefix = "/".join(prefix_parts[:-1])
                canon_id = f"{dir_prefix}/{local_name}"
            else:
                # No subdirectories - just section name
                canon_id = local_name

            acc[canon_id] = SectionCfg.from_dict(canon_id, node)
            continue

        # Rule 2: multiple sections → normalize "tail" by prefix
        pref_tail = prefix.split("/")[-1] if prefix else ""
        for local_name, node in section_items:
            if not isinstance(node, dict):
                raise RuntimeError(f"Section '{local_name}' in {frag} must be a mapping")
            # Normalize canon-ID without repeating tail (fixes "a/a" etc.)
            canon_id = prefix if (pref_tail and local_name == pref_tail) else f"{prefix}/{local_name}"
            acc[canon_id] = SectionCfg.from_dict(canon_id, node)
    return acc


def load_config(root: Path) -> Config:
    """
    Schema:
      • lg-cfg/sections.yaml — file with base sections
      • lg-cfg/**/*.sec.yaml — arbitrary number of section fragments
    """
    base = cfg_root(root)
    if not base.is_dir():
        raise RuntimeError(f"Config directory not found: {base}")
    # Before any reading, bring lg-cfg/ to current format
    ensure_cfg_actual(base)

    core_sections = _collect_sections_from_sections_yaml(root)
    frag_sections = _collect_sections_from_fragments(root)

    # Merge with duplicate canonical ID check
    all_sections: Dict[str, SectionCfg] = dict(core_sections)
    for k, v in frag_sections.items():
        if k in all_sections:
            raise RuntimeError(f"Duplicate section id: '{k}'")
        all_sections[k] = v

    return Config(sections=all_sections)


def list_sections(root: Path) -> List[str]:
    """
    Strict list (via load_config) — MIGRATIONS POSSIBLE.
    Used where format is guaranteed to be up-to-date.
    """
    cfg = load_config(root)
    return sorted(cfg.sections.keys())

def list_sections_peek(root: Path) -> List[str]:
    """
    Safe list without running migrations.
    Reads lg-cfg/sections.yaml and all **/*.sec.yaml directly.
    """
    base = cfg_root(root)
    if not base.is_dir():
        return []
    core = _collect_sections_from_sections_yaml(root)
    frags = _collect_sections_from_fragments(root)
    return sorted({*core.keys(), *frags.keys()})
