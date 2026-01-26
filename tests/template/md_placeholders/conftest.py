"""
Test infrastructure for markdown placeholders.

Provides fixtures and helpers for creating temporary projects
with Markdown files and testing markdown placeholders like ${md:...}.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Import from unified infrastructure
from tests.infrastructure import write, write_markdown, render_template, make_run_options
from tests.infrastructure.config_builders import create_basic_lg_cfg, create_template


# ====================== Main Fixtures ======================

@pytest.fixture
def md_project(tmp_path: Path) -> Path:
    """
    Creates a basic project for testing markdown placeholders.

    Includes:
    - Minimal lg-cfg configuration
    - Several test Markdown files
    - Basic directory structure
    """
    root = tmp_path

    # Create basic configuration
    create_basic_lg_cfg(root)

    # Create test Markdown files
    write_markdown(root / "README.md",
                   title="Main Project",
                   content="This is the main project documentation.\n\n## Features\n\n- Feature A\n- Feature B")

    write_markdown(root / "docs" / "guide.md",
                   title="User Guide",
                   content="This is a comprehensive user guide.\n\n## Installation\n\nRun the installer.\n\n## Usage\n\nUse the app.")

    write_markdown(root / "docs" / "api.md",
                   title="API Reference",
                   content="API documentation.\n\n## Authentication\n\nUse API keys.\n\n## Endpoints\n\n### GET /users\n\nGet users list.")

    # File without H1 for strip_h1 tests
    write_markdown(root / "docs" / "changelog.md",
                   title="",
                   content="## v1.0.0\n\n- Initial release\n\n## v0.9.0\n\n- Beta version")

    # File in lg-cfg for @self: tests
    write_markdown(root / "lg-cfg" / "internal.md",
                   title="Internal Documentation",
                   content="This is internal documentation stored in lg-cfg.")

    return root


@pytest.fixture
def federated_md_project(tmp_path: Path) -> Path:
    """
    Creates a project with federated structure for testing addressed markdown placeholders.
    """
    root = tmp_path

    # Root configuration
    create_basic_lg_cfg(root)

    # Root documents
    write_markdown(root / "README.md",
                  title="Federated Project",
                  content="Main project in a monorepo structure.")

    # Internal documentation in lg-cfg
    write_markdown(root / "lg-cfg" / "internal.md",
                  title="Internal Documentation",
                  content="Internal documentation for the federated project.")

    # === Child scope: apps/web ===
    create_basic_lg_cfg(root / "apps" / "web")

    write_markdown(root / "apps" / "web" / "web-readme.md",
                  title="Web Application",
                  content="Frontend web application.\n\n## Components\n\n- Header\n- Footer\n- Main content")

    write_markdown(root / "apps" / "web" / "lg-cfg" / "deployment.md",
                  title="Web Deployment Guide",
                  content="How to deploy the web app.\n\n## Build\n\nnpm run build\n\n## Deploy\n\nDeploy to staging.")

    # === Child scope: libs/utils ===
    create_basic_lg_cfg(root / "libs" / "utils")

    write_markdown(root / "libs" / "utils" / "utils-readme.md",
                  title="Utility Library",
                  content="Shared utility functions.\n\n## Math Utils\n\n- add()\n- multiply()\n\n## String Utils\n\n- capitalize()\n- trim()")
    
    return root


@pytest.fixture
def adaptive_md_project(tmp_path: Path) -> Path:
    """
    Creates a project with adaptive capabilities for testing conditional markdown placeholders.
    """
    root = tmp_path

    # Create basic configuration
    create_basic_lg_cfg(root)

    # Create documents for conditional inclusion
    write_markdown(root / "deployment" / "cloud.md",
                  title="Cloud Deployment",
                  content="Instructions for cloud deployment.\n\n## AWS\n\nUse CloudFormation.\n\n## Azure\n\nUse ARM templates.")
    
    write_markdown(root / "deployment" / "onprem.md", 
                  title="On-Premises Deployment",
                  content="Instructions for on-premises deployment.\n\n## Requirements\n\n- Docker\n- Kubernetes")
    
    write_markdown(root / "basic" / "intro.md",
                  title="Introduction", 
                  content="Basic introduction to the project.")
    
    return root


# ====================== Glob Helpers ======================

def create_glob_test_files(root: Path) -> None:
    """Creates a set of files for testing globs."""

    # Create several files in docs/
    write_markdown(root / "docs" / "overview.md",
                  title="Overview",
                  content="Project overview")

    write_markdown(root / "docs" / "tutorial.md",
                  title="Tutorial",
                  content="Step by step tutorial")

    write_markdown(root / "docs" / "faq.md",
                  title="FAQ",
                  content="Frequently asked questions")

    # Create files in subdirectories
    write_markdown(root / "docs" / "advanced" / "internals.md",
                  title="Internals",
                  content="Internal architecture")

    write_markdown(root / "docs" / "advanced" / "plugins.md",
                  title="Plugins",
                  content="Plugin development")


# ====================== Exports ======================

__all__ = [
    # Main fixtures
    "md_project", "federated_md_project", "adaptive_md_project",

    # File creation helpers
    "write", "write_markdown", "create_basic_lg_cfg", "create_template",

    # Rendering helpers
    "render_template", "make_run_options",

    # Glob helpers
    "create_glob_test_files"
]