"""
Builders for creating configuration YAML files in tests.

Unifies creation of sections.yaml, meta-sections, and other configs.
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
                      Default: ["ai-interaction"] (only what's auto-created).
                      For full adaptive features, use adaptive_project fixture or pass
                      ["ai-interaction", "dev-stage", "tags"] and create those meta-sections.
        create_meta_sections: If True, automatically create ai-interaction meta-section.
                              Default: True.
    """
    if extends_from is None:
        extends_from = ["ai-interaction"]

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
# Meta-section builders
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
                    # Spread extra options directly into mode dict
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
                    title="Agent work",
                    description="Mode with tools",
                    tags=["agent", "tools"],
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
    # YAML builders
    "create_sections_yaml", "create_section_fragment",

    # Simple builders
    "create_basic_lg_cfg", "create_basic_sections_yaml", "create_template",

    # Predefined configs
    "get_basic_sections_config", "get_multilang_sections_config",

    # Meta-section builders
    "create_mode_meta_section", "create_tag_meta_section",
    "create_integration_mode_section", "create_adaptive_section",
]