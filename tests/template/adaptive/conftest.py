"""
Test infrastructure for adaptive features.

Provides fixtures for creating temporary projects with configured modes,
tags, and federated structure for testing the adaptive system of Listing Generator.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader, process_adaptive_options
from lg.run_context import RunContext
from lg.stats.tokenizer import default_tokenizer
from lg.types import RunOptions
from lg.git import NullVcs

# Import from unified infrastructure
from tests.infrastructure import (
    write, create_modes_yaml, create_tags_yaml, create_basic_sections_yaml,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig,
    make_run_options, make_engine, render_template
)


def get_default_modes_config() -> Dict[str, ModeSetConfig]:
    """Returns standard mode configuration for tests."""
    return {
        "ai-interaction": ModeSetConfig(
            title="AI interaction method",
            modes={
                "ask": ModeConfig(
                    title="Ask",
                    description="Basic question-answer mode"
                ),
                "agent": ModeConfig(
                    title="Agent work",
                    description="Mode with tools",
                    tags=["agent", "tools"],
                    options={"allow_tools": True}
                )
            }
        ),
        "dev-stage": ModeSetConfig(
            title="Development stage",
            modes={
                "planning": ModeConfig(
                    title="Planning",
                    tags=["architecture", "docs"]
                ),
                "development": ModeConfig(
                    title="Main development"
                ),
                "testing": ModeConfig(
                    title="Test writing",
                    tags=["tests"]
                ),
                "review": ModeConfig(
                    title="Code review",
                    tags=["review"],
                    options={"vcs_mode": "changes"}
                )
            }
        )
    }


def get_default_tags_config() -> tuple[Dict[str, TagSetConfig], Dict[str, TagConfig]]:
    """Returns standard tag configuration for tests."""
    tag_sets = {
        "language": TagSetConfig(
            title="Programming languages",
            tags={
                "python": TagConfig(title="Python"),
                "typescript": TagConfig(title="TypeScript"),
                "javascript": TagConfig(title="JavaScript")
            }
        ),
        "code-type": TagSetConfig(
            title="Code type",
            tags={
                "product": TagConfig(title="Product code"),
                "tests": TagConfig(title="Test code"),
                "generated": TagConfig(title="Generated code")
            }
        )
    }

    global_tags = {
        "agent": TagConfig(title="Agent capabilities"),
        "review": TagConfig(title="Code review rules"),
        "architecture": TagConfig(title="Architecture documentation"),
        "docs": TagConfig(title="Documentation"),
        "tests": TagConfig(title="Test code"),
        "tools": TagConfig(title="Tools"),
        "minimal": TagConfig(title="Minimal version")
    }

    return tag_sets, global_tags


# ====================== RunOptions helpers ======================


def make_run_context(root: Path, options: Optional[RunOptions] = None) -> RunContext:
    """
    Creates RunContext for testing.

    Args:
        root: Project root
        options: Run options

    Returns:
        Configured RunContext
    """
    if options is None:
        options = make_run_options()

    cache = Cache(root, enabled=None, fresh=False, tool_version="test")
    adaptive_loader = AdaptiveConfigLoader(root)

    # Use process_adaptive_options for proper active_tags initialization
    active_tags, mode_options, _ = process_adaptive_options(
        root,
        options.modes,
        options.extra_tags
    )

    return RunContext(
        root=root,
        options=options,
        cache=cache,
        vcs=NullVcs(),
        tokenizer=default_tokenizer(),
        adaptive_loader=adaptive_loader,
        mode_options=mode_options,
        active_tags=active_tags
    )


# ====================== Main fixtures ======================

@pytest.fixture
def adaptive_project(tmp_path: Path) -> Path:
    """
    Creates a basic project with adaptive features.

    Includes:
    - Standard modes and tags
    - Basic sections
    - Several source files for testing
    """
    root = tmp_path

    # Create mode configuration
    mode_sets = get_default_modes_config()
    create_modes_yaml(root, mode_sets)

    # Create tag configuration
    tag_sets, global_tags = get_default_tags_config()
    create_tags_yaml(root, tag_sets, global_tags)

    # Create basic sections
    create_basic_sections_yaml(root)

    # Create test files
    write(root / "src" / "main.py", "def main():\n    print('Hello, world!')\n")
    write(root / "src" / "utils.py", "def helper():\n    return 42\n")
    write(root / "docs" / "README.md", "# Project Documentation\n\nThis is a test project.\n")
    write(root / "tests" / "test_main.py", "def test_main():\n    assert True\n")

    return root


@pytest.fixture
def minimal_adaptive_project(tmp_path: Path) -> Path:
    """
    Creates a minimal project with one mode and tag.
    Useful for simple tests.
    """
    root = tmp_path

    # Minimal mode configuration
    mode_sets = {
        "simple": ModeSetConfig(
            title="Simple mode",
            modes={
                "default": ModeConfig(title="Default"),
                "minimal": ModeConfig(
                    title="Minimal",
                    tags=["minimal"]
                )
            }
        )
    }
    create_modes_yaml(root, mode_sets)

    # Minimal tag configuration
    global_tags = {
        "minimal": TagConfig(title="Minimal version")
    }
    create_tags_yaml(root, global_tags=global_tags)

    # Simple section
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    all:
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/**"
    """).strip() + "\n")

    # One test file
    write(root / "main.py", "print('minimal')\n")

    return root


@pytest.fixture
def federated_project(tmp_path: Path) -> Path:
    """
    Creates a project with federated structure (monorepo).

    Includes:
    - Root lg-cfg with basic configuration
    - Child scope apps/web with its own configuration
    - Child scope libs/core with its own configuration
    - Mutual inclusions between scopes
    """
    root = tmp_path

    # Root mode configuration with inclusions
    root_modes = {
        "workflow": ModeSetConfig(
            title="Workflow",
            modes={
                "full": ModeConfig(
                    title="Full overview",
                    tags=["full-context"]
                )
            }
        )
    }
    create_modes_yaml(root, root_modes, include=["apps/web", "libs/core"])

    # Root tag configuration
    root_tags = {
        "full-context": TagConfig(title="Full context")
    }
    create_tags_yaml(root, global_tags=root_tags, include=["apps/web", "libs/core"])

    # Root sections
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    overview:
      extensions: [".md"]
      filters:
        mode: allow
        allow:
          - "/README.md"
          - "/docs/**"
    """).strip() + "\n")

    # === Child scope: apps/web ===
    web_modes = {
        "frontend": ModeSetConfig(
            title="Frontend work",
            modes={
                "ui": ModeConfig(
                    title="UI components",
                    tags=["typescript", "ui"]
                ),
                "api": ModeConfig(
                    title="API integration",
                    tags=["typescript", "api"]
                )
            }
        )
    }
    create_modes_yaml(root / "apps" / "web", web_modes)

    web_tag_sets = {
        "frontend-type": TagSetConfig(
            title="Frontend code type",
            tags={
                "ui": TagConfig(title="UI components"),
                "api": TagConfig(title="API layer")
            }
        )
    }
    web_global_tags = {
        "typescript": TagConfig(title="TypeScript code")
    }
    create_tags_yaml(root / "apps" / "web", web_tag_sets, web_global_tags)

    write(root / "apps" / "web" / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    web-src:
      extensions: [".ts", ".tsx"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n")

    # === Child scope: libs/core ===
    core_modes = {
        "library": ModeSetConfig(
            title="Library development",
            modes={
                "public-api": ModeConfig(
                    title="Public API",
                    tags=["python", "api-only"]
                ),
                "internals": ModeConfig(
                    title="Internal implementation",
                    tags=["python", "full-impl"]
                )
            }
        )
    }
    create_modes_yaml(root / "libs" / "core", core_modes)

    core_global_tags = {
        "python": TagConfig(title="Python code"),
        "api-only": TagConfig(title="Public API only"),
        "full-impl": TagConfig(title="Full implementation")
    }
    create_tags_yaml(root / "libs" / "core", global_tags=core_global_tags)

    write(root / "libs" / "core" / "lg-cfg" / "sections.yaml", textwrap.dedent("""
    core-lib:
      extensions: [".py"]
      python:
        when:
          - condition: "tag:api-only"
            strip_function_bodies: true
      filters:
        mode: allow
        allow:
          - "/core/**"
    """).strip() + "\n")

    # Test files
    write(root / "README.md", "# Federated Project\n\nMain project documentation.\n")
    write(root / "docs" / "arch.md", "# Architecture\n\nSystem architecture overview.\n")
    write(root / "apps" / "web" / "src" / "App.tsx", "export function App() { return <div>Hello</div>; }\n")
    write(root / "libs" / "core" / "core" / "__init__.py", "def public_api():\n    return _internal()\n\ndef _internal():\n    return 'core'\n")

    return root


# ====================== Template helpers ======================

def create_conditional_template(
    root: Path,
    name: str,
    content: str,
    template_type: str = "ctx"
) -> Path:
    """
    Creates a template with conditional logic.

    Args:
        root: Project root
        name: Template name (without extension)
        content: Template content with conditional blocks
        template_type: Template type ("ctx" or "tpl")

    Returns:
        Path to created file
    """
    suffix = f".{template_type}.md"
    return write(root / "lg-cfg" / f"{name}{suffix}", content)


def create_mode_template(
    root: Path,
    name: str,
    sections_by_mode: Dict[str, List[str]],
    template_type: str = "ctx"
) -> Path:
    """
    Creates a template with mode blocks.

    Args:
        root: Project root
        name: Template name
        sections_by_mode: Dictionary {mode_spec: [section_names]}
        template_type: Template type

    Returns:
        Path to created file
    """
    content_parts = [f"# Template {name}\n"]

    for mode_spec, sections in sections_by_mode.items():
        content_parts.append(f"\n{{% mode {mode_spec} %}}")
        for section in sections:
            content_parts.append(f"${{{section}}}")
        content_parts.append("{% endmode %}\n")

    content = "\n".join(content_parts)
    return create_conditional_template(root, name, content, template_type)


# ====================== Exports ======================

__all__ = [
    # Configuration types
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",

    # Configuration creation helpers
    "create_modes_yaml", "create_tags_yaml", "create_basic_sections_yaml",

    # Ready-made configurations
    "get_default_modes_config", "get_default_tags_config",

    # RunOptions and context helpers
    "make_run_options", "make_run_context", "make_engine", "render_template",

    # Main fixtures
    "adaptive_project", "minimal_adaptive_project", "federated_project",

    # Template helpers
    "create_conditional_template", "create_mode_template"
]