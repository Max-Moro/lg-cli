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


def create_basic_lg_cfg(root: Path, with_integration_mode: bool = True) -> Path:
    """
    Creates minimal configuration lg-cfg/sections.yaml.

    Args:
        root: Project root
        with_integration_mode: If True, also create ai-interaction meta-section
                               and add extends to sections. Default: True.
    """
    if with_integration_mode:
        create_integration_mode_section(root)
        content = textwrap.dedent("""
        all:
          extends: ["ai-interaction"]
          extensions: [".md"]
          markdown:
            max_heading_level: 2
          filters:
            mode: allow
            allow:
              - "/**"
        """).strip() + "\n"
    else:
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


def create_template(
    root: Path,
    name: str,
    content: str,
    template_type: str = "ctx",
    include_meta_sections: Optional[List[str]] = None
) -> Path:
    """
    Creates a template or context.

    Args:
        root: Project root
        name: File name (without extension)
        content: Template content
        template_type: Type ("ctx" or "tpl")
        include_meta_sections: List of meta-sections to include via frontmatter.
                               Only applicable for "ctx" type. If ["ai-interaction"]
                               is in the list, the meta-section will be auto-created.
                               Default: ["ai-interaction"] for ctx type.

    Returns:
        Path to the created file
    """
    # Default: add ai-interaction for context files
    if include_meta_sections is None and template_type == "ctx":
        include_meta_sections = ["ai-interaction"]

    # Create meta-sections and add frontmatter if needed
    final_content = content
    if include_meta_sections and template_type == "ctx":
        # Create ai-interaction meta-section if needed
        if "ai-interaction" in include_meta_sections:
            create_integration_mode_section(root)

        # Add frontmatter
        include_yaml = ", ".join(f'"{s}"' for s in include_meta_sections)
        frontmatter = f"---\ninclude: [{include_yaml}]\n---\n"
        final_content = frontmatter + content

    suffix = f".{template_type}.md"
    return write(root / "lg-cfg" / f"{name}{suffix}", final_content)


def create_basic_sections_yaml(
    root: Path,
    extends_from: Optional[List[str]] = None,
    create_meta_sections: bool = True
) -> Path:
    """
    Creates basic sections.yaml for tests (from adaptive tests).

    Args:
        root: Project root
        extends_from: List of meta-sections to inherit from (for adaptive features).
                      Default: ["ai-interaction", "dev-stage", "tags"] to ensure all adaptive features are available.
        create_meta_sections: If True, automatically create meta-sections referenced in extends_from.
                              Default: True.
    """
    if extends_from is None:
        extends_from = ["ai-interaction", "dev-stage", "tags"]

    # Create referenced meta-sections if requested
    if create_meta_sections and "ai-interaction" in extends_from:
        create_integration_mode_section(root)

    # Build extends line if needed (with proper YAML indentation)
    extends_line = ""
    if extends_from:
        extends_yaml = ", ".join(f'"{s}"' for s in extends_from)
        extends_line = f"extends: [{extends_yaml}]\n  "

    content = f"""src:
  {extends_line}extensions: [".py", ".md"]
  filters:
    mode: allow
    allow:
      - "/src/**"

docs:
  {extends_line}extensions: [".md"]
  markdown:
    max_heading_level: 2
  filters:
    mode: allow
    allow:
      - "/docs/**"

tests:
  {extends_line}extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/tests/**"
"""

    return write(root / "lg-cfg" / "sections.yaml", content)


# Pre-built section configurations
def get_basic_sections_config(with_extends: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Returns basic sections configuration for tests.

    Args:
        with_extends: If True, adds extends: ["ai-interaction"] to all sections.
    """
    extends_part = {"extends": ["ai-interaction"]} if with_extends else {}

    return {
        "src": {
            **extends_part,
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        },
        "docs": {
            **extends_part,
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
            **extends_part,
            "extensions": [".py", ".md", ".ts"],
            "filters": {
                "mode": "allow",
                "allow": ["/**"]
            }
        },
        "tests": {
            **extends_part,
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
                "skip_trivial_files": True
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


# =============================================================================
# NEW: Meta-section builders for new adaptive system
# =============================================================================

def create_mode_meta_section(
    root: Path,
    section_name: str,
    mode_sets: Dict[str, Any],
    extends: Optional[List[str]] = None,
) -> Path:
    """
    Creates a meta-section file with mode-sets (no filters).

    Meta-sections are used for storing adaptive configuration
    and can be inherited via `extends`.

    Args:
        root: Project root
        section_name: Section name (will create {section_name}.sec.yaml)
        mode_sets: Dictionary of mode sets (can be ModeSetConfig or dict)
        extends: List of sections to inherit from

    Returns:
        Path to the created file
    """
    section_file = root / "lg-cfg" / f"{section_name}.sec.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    section_data = {}

    # Add extends if provided
    if extends:
        section_data["extends"] = extends

    # Convert mode_sets to proper format
    if mode_sets:
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
                    if hasattr(mode, 'runs') and mode.runs:
                        mode_dict["runs"] = mode.runs
                    if hasattr(mode, 'default_task') and mode.default_task:
                        mode_dict["default_task"] = mode.default_task
                    if hasattr(mode, 'vcs_mode') and mode.vcs_mode:
                        mode_dict["vcs_mode"] = mode.vcs_mode
                    # Legacy: add options directly to mode dict
                    if hasattr(mode, 'options') and mode.options:
                        mode_dict.update(mode.options)
                    modes_dict[mode_name] = mode_dict

                new_mode_sets[set_name] = {
                    "title": mode_set.title,
                    "modes": modes_dict
                }
            else:
                new_mode_sets[set_name] = mode_set
        section_data["mode-sets"] = new_mode_sets

    # Wrap in section name
    final_data = {section_name: section_data}

    section_file.parent.mkdir(parents=True, exist_ok=True)
    with section_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)

    return section_file


def create_tag_meta_section(
    root: Path,
    section_name: str,
    tag_sets: Optional[Dict[str, Any]] = None,
    extends: Optional[List[str]] = None,
) -> Path:
    """
    Creates a meta-section file with tag-sets (no filters).

    Args:
        root: Project root
        section_name: Section name (will create {section_name}.sec.yaml)
        tag_sets: Dictionary of tag sets (can be TagSetConfig or dict)
        extends: List of sections to inherit from

    Returns:
        Path to the created file
    """
    section_file = root / "lg-cfg" / f"{section_name}.sec.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    section_data = {}

    # Add extends if provided
    if extends:
        section_data["extends"] = extends

    # Convert tag_sets to proper format
    if tag_sets:
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
        section_data["tag-sets"] = new_tag_sets

    # Wrap in section name
    final_data = {section_name: section_data}

    section_file.parent.mkdir(parents=True, exist_ok=True)
    with section_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)

    return section_file


def create_integration_mode_section(
    root: Path,
    section_name: str = "ai-interaction",
    providers: Optional[List[str]] = None,
) -> Path:
    """
    Creates a standard integration meta-section for AI interaction modes.

    This is the canonical meta-section that IDE plugins expect.
    Contains modes with 'runs' field for different providers.

    Args:
        root: Project root
        section_name: Section name (default: "ai-interaction")
        providers: List of provider IDs to include (default: test provider)

    Returns:
        Path to the created file
    """
    if providers is None:
        providers = ["com.test.provider"]

    # Build runs dict for each mode
    ask_runs = {p: f"--mode ask" for p in providers}
    agent_runs = {p: f"--mode agent" for p in providers}

    from .adaptive_config import ModeConfig, ModeSetConfig

    mode_sets = {
        section_name: ModeSetConfig(
            title="AI Interaction",
            modes={
                "ask": ModeConfig(
                    title="Ask",
                    description="Question-answer mode",
                    runs=ask_runs,
                ),
                "agent": ModeConfig(
                    title="Agent",
                    description="Agent mode with tools",
                    tags=["agent"],
                    runs=agent_runs,
                ),
            }
        )
    }

    return create_mode_meta_section(root, section_name, mode_sets)


def create_adaptive_section(
    root: Path,
    section_name: str,
    mode_sets: Optional[Dict[str, Any]] = None,
    tag_sets: Optional[Dict[str, Any]] = None,
    extends: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    extensions: Optional[List[str]] = None,
) -> Path:
    """
    Creates a section with both mode-sets and tag-sets.

    Can be either a meta-section (no filters) or a regular section (with filters).

    Args:
        root: Project root
        section_name: Section name
        mode_sets: Dictionary of mode sets
        tag_sets: Dictionary of tag sets
        extends: List of sections to inherit from
        filters: Filter configuration (if provided, creates regular section)
        extensions: File extensions (required if filters provided)

    Returns:
        Path to the created file
    """
    section_file = root / "lg-cfg" / f"{section_name}.sec.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True

    section_data = {}

    # Add extends if provided
    if extends:
        section_data["extends"] = extends

    # Add extensions if provided
    if extensions:
        section_data["extensions"] = extensions

    # Add filters if provided (makes it a regular section, not meta)
    if filters:
        section_data["filters"] = filters

    # Convert and add mode_sets
    if mode_sets:
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
                    if hasattr(mode, 'runs') and mode.runs:
                        mode_dict["runs"] = mode.runs
                    if hasattr(mode, 'default_task') and mode.default_task:
                        mode_dict["default_task"] = mode.default_task
                    if hasattr(mode, 'vcs_mode') and mode.vcs_mode:
                        mode_dict["vcs_mode"] = mode.vcs_mode
                    if hasattr(mode, 'options') and mode.options:
                        mode_dict.update(mode.options)
                    modes_dict[mode_name] = mode_dict

                new_mode_sets[set_name] = {
                    "title": mode_set.title,
                    "modes": modes_dict
                }
            else:
                new_mode_sets[set_name] = mode_set
        section_data["mode-sets"] = new_mode_sets

    # Convert and add tag_sets
    if tag_sets:
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
        section_data["tag-sets"] = new_tag_sets

    # Wrap in section name
    final_data = {section_name: section_data}

    section_file.parent.mkdir(parents=True, exist_ok=True)
    with section_file.open("w", encoding="utf-8") as f:
        yaml.dump(final_data, f)

    return section_file


__all__ = [
    # YAML builders (all support configuration classes)
    "create_sections_yaml", "create_section_fragment", "create_modes_yaml", "create_tags_yaml",

    # Simple builders
    "create_basic_lg_cfg", "create_basic_sections_yaml", "create_template",

    # Predefined configs
    "get_basic_sections_config", "get_multilang_sections_config",

    # NEW: Meta-section builders for new adaptive system
    "create_mode_meta_section", "create_tag_meta_section",
    "create_integration_mode_section", "create_adaptive_section",
]