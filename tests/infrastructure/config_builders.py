"""
Builders for creating configuration YAML files in tests.

Unifies creation of sections.yaml, modes.yaml, tags.yaml and other configs.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Any

from ruamel.yaml import YAML

from .file_utils import write


def create_sections_yaml(root: Path, sections_config: Dict[str, Dict[str, Any]]) -> Path:
    """
    Creates lg-cfg/sections.yaml with specified sections.

    Args:
        root: Project root
        sections_config: Sections configuration dictionary

    Returns:
        Path to the created file
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
    Creates a section fragment *.sec.yaml.

    Args:
        root: Project root
        fragment_path: Path to fragment file relative to lg-cfg/
        sections_config: Sections configuration dictionary

    Returns:
        Path to the created file
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
    Creates modes.yaml file with specified mode sets.

    Args:
        root: Project root
        mode_sets: Dictionary of mode sets (can be ModeSetConfig or dict)
        include: List of child scopes to include
        append: If True, appends to existing configuration

    Returns:
        Path to the created file
    """
    modes_file = root / "lg-cfg" / "modes.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing configuration if append=True
    existing_data = {}
    if append and modes_file.exists():
        with modes_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}

    new_data = {}

    if mode_sets:
        # Support both plain dict and structured objects
        if isinstance(list(mode_sets.values())[0], dict):
            new_data["mode-sets"] = mode_sets
        else:
            # Convert from ModeSetConfig to dict (if needed)
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

    # Merge with existing data if append=True
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

    # Write back
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
    Creates tags.yaml file with specified tag sets.

    Args:
        root: Project root
        tag_sets: Dictionary of tag sets (can be TagSetConfig or dict)
        global_tags: Dictionary of global tags (can be TagConfig or dict)
        include: List of child scopes to include
        append: If True, appends to existing configuration

    Returns:
        Path to the created file
    """
    tags_file = root / "lg-cfg" / "tags.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    # Load existing configuration if append=True
    existing_data = {}
    if append and tags_file.exists():
        with tags_file.open(encoding="utf-8") as f:
            existing_data = yaml.load(f) or {}

    new_data = {}

    if tag_sets:
        # Support both plain dict and structured objects
        if isinstance(list(tag_sets.values())[0], dict):
            new_data["tag-sets"] = tag_sets
        else:
            # Convert from TagSetConfig to dict
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
        # Support both plain dict and TagConfig objects
        if isinstance(list(global_tags.values())[0], dict):
            new_data["tags"] = global_tags
        else:
            # Convert from TagConfig to dict
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

    # Merge with existing data if append=True
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

    # Write back
    tags_file.parent.mkdir(parents=True, exist_ok=True)
    with tags_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)

    return tags_file


def create_basic_lg_cfg(root: Path) -> Path:
    """Creates minimal configuration lg-cfg/sections.yaml."""
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
    Creates a template or context.

    Args:
        root: Project root
        name: File name (without extension)
        content: Template content
        template_type: Type ("ctx" or "tpl")

    Returns:
        Path to the created file
    """
    suffix = f".{template_type}.md"
    return write(root / "lg-cfg" / f"{name}{suffix}", content)


def create_basic_sections_yaml(root: Path) -> Path:
    """Creates basic sections.yaml for tests (from adaptive tests)."""
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


# Pre-built section configurations
def get_basic_sections_config() -> Dict[str, Dict[str, Any]]:
    """Returns basic sections configuration for tests."""
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
    """Returns sections configuration for multilingual projects."""
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
    # YAML builders (all support configuration classes)
    "create_sections_yaml", "create_section_fragment", "create_modes_yaml", "create_tags_yaml",

    # Simple builders
    "create_basic_lg_cfg", "create_basic_sections_yaml", "create_template",

    # Predefined configs
    "get_basic_sections_config", "get_multilang_sections_config"
]