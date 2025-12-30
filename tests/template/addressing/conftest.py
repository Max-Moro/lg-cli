"""
Fixtures for addressing package tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.infrastructure import write


@pytest.fixture
def addressing_project(tmp_path: Path) -> Path:
    """
    Create minimal project with lg-cfg structure for resolver tests.

    Structure:
        root/
        ├── lg-cfg/
        │   ├── sections.yaml
        │   ├── intro.tpl.md
        │   ├── main.ctx.md
        │   ├── common/
        │   │   └── header.tpl.md
        │   └── docs/
        │       ├── api.tpl.md
        │       └── guide.md
        └── README.md
    """
    root = tmp_path
    cfg = root / "lg-cfg"

    # Root files
    write(cfg / "sections.yaml", "docs:\n  extensions: ['.md']")
    write(cfg / "intro.tpl.md", "# Introduction")
    write(cfg / "main.ctx.md", "# Main Context")

    # Common directory
    write(cfg / "common" / "header.tpl.md", "# Header")

    # Docs directory
    write(cfg / "docs" / "api.tpl.md", "# API Docs")
    write(cfg / "docs" / "guide.md", "# Guide")

    # External markdown (outside lg-cfg)
    write(root / "README.md", "# Project README")
    write(root / "docs" / "external.md", "# External Docs")

    return root


@pytest.fixture
def multi_scope_project(tmp_path: Path) -> Path:
    """
    Create project with multiple lg-cfg scopes for testing cross-scope resolution.

    Structure:
        root/
        ├── lg-cfg/
        │   ├── sections.yaml
        │   └── root.tpl.md
        ├── apps/
        │   └── web/
        │       └── lg-cfg/
        │           ├── sections.yaml
        │           └── web.tpl.md
        └── libs/
            └── core/
                └── lg-cfg/
                    ├── sections.yaml
                    └── core.tpl.md
    """
    root = tmp_path

    # Root lg-cfg
    write(root / "lg-cfg" / "sections.yaml", "root-docs:\n  extensions: ['.md']")
    write(root / "lg-cfg" / "root.tpl.md", "# Root Template")

    # apps/web lg-cfg
    write(root / "apps" / "web" / "lg-cfg" / "sections.yaml", "web-src:\n  extensions: ['.py']")
    write(root / "apps" / "web" / "lg-cfg" / "web.tpl.md", "# Web Template")

    # libs/core lg-cfg
    write(root / "libs" / "core" / "lg-cfg" / "sections.yaml", "core-src:\n  extensions: ['.py']")
    write(root / "libs" / "core" / "lg-cfg" / "core.tpl.md", "# Core Template")

    return root
