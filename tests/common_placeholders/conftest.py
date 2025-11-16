"""
Test infrastructure for section and template placeholders.

Provides fixtures and helpers for creating temporary projects
with sections, templates, and contexts for testing the main
functionality of the Listing Generator template engine.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict

import pytest

# Import from unified infrastructure
from tests.infrastructure import (
    write, write_source_file,
    create_sections_yaml, create_template, create_section_fragment,
    render_template, make_run_options,
    get_basic_sections_config, get_multilang_sections_config
)


@pytest.fixture
def basic_project(tmp_path: Path) -> Path:
    """
    Creates a basic project for testing section and template placeholders.

    Includes:
    - Standard sections (src, docs, all, tests)
    - Several source files of different types
    - Basic directory structure
    """
    root = tmp_path

    # Create sections
    sections_config = get_basic_sections_config()
    create_sections_yaml(root, sections_config)

    # Create source files
    write_source_file(root / "src" / "main.py",
                     "def main():\n    print('Hello from main')\n    return 0")

    write_source_file(root / "src" / "utils.py",
                     "def helper_function(x):\n    return x * 2\n\nclass Helper:\n    pass")

    write_source_file(root / "src" / "config.py",
                     "CONFIG = {\n    'app_name': 'test',\n    'version': '1.0.0'\n}")

    # Create documentation
    write(root / "docs" / "README.md", textwrap.dedent("""
        # Project Documentation

        This is the main project documentation.

        ## Features

        - Feature A: Core functionality
        - Feature B: Additional utilities

        ## Usage

        See the API reference for details.
        """).strip() + "\n")

    write(root / "docs" / "api.md", textwrap.dedent("""
        # API Reference

        ## Functions

        ### main()

        Main entry point.

        ### helper_function(x)

        Helper utility function.
        """).strip() + "\n")

    # Create test files
    write_source_file(root / "tests" / "test_main.py",
                     "def test_main():\n    assert True\n\ndef test_helper():\n    assert helper_function(2) == 4")

    return root


@pytest.fixture
def multilang_project(tmp_path: Path) -> Path:
    """
    Creates a multilingual project for testing complex configurations.

    Includes:
    - Python and TypeScript files
    - Specialized sections for different languages
    - Shared documentation
    """
    root = tmp_path

    # Create specialized sections
    sections_config = get_multilang_sections_config()
    create_sections_yaml(root, sections_config)

    # Python files
    write_source_file(root / "python" / "__init__.py", "", "python")
    write_source_file(root / "python" / "core.py",
                     "class Core:\n    def process(self):\n        pass", "python")

    # TypeScript files
    write_source_file(root / "typescript" / "app.ts",
                     "export class App {\n  run(): void {\n    console.log('Running');\n  }\n}", "typescript")

    write_source_file(root / "typescript" / "utils.tsx",
                     "import React from 'react';\n\nexport const Component = () => <div>Hello</div>;", "typescript")

    # Shared documentation
    write(root / "shared-docs" / "architecture.md", textwrap.dedent("""
        # Architecture Overview

        This project uses a multilingual approach:

        ## Backend (Python)

        Core business logic implementation.

        ## Frontend (TypeScript)

        User interface and interaction layer.
        """).strip() + "\n")

    return root


@pytest.fixture
def federated_project(tmp_path: Path) -> Path:
    """
    Creates a federated project (monorepo) for testing addressed links.

    Includes:
    - Root lg-cfg with basic sections
    - Child scope apps/web with its own sections
    - Child scope libs/core with its own sections
    - Cross-scope dependencies
    """
    root = tmp_path

    # === Root sections ===
    root_sections = {
        "overview": {
            "extensions": [".md"],
            "filters": {
                "mode": "allow",
                "allow": ["/README.md", "/docs/**"]
            }
        },
        "root-config": {
            "extensions": [".json", ".yaml"],
            "filters": {
                "mode": "allow",
                "allow": ["/*.json", "/*.yaml"]
            }
        }
    }
    create_sections_yaml(root, root_sections)

    # Root files
    write(root / "README.md", textwrap.dedent("""
        # Federated Project

        This is a monorepo with multiple modules.

        ## Structure

        - apps/web - Web application
        - libs/core - Core library
        """).strip() + "\n")

    write(root / "docs" / "overview.md", textwrap.dedent("""
        # Project Overview

        Comprehensive project documentation.
        """).strip() + "\n")

    # === Child scope: apps/web ===
    web_sections = {
        "web-src": {
            "extensions": [".ts", ".tsx"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        },
        "web-docs": {
            "extensions": [".md"],
            "filters": {
                "mode": "allow",
                "allow": ["/docs/**"]
            }
        }
    }
    create_sections_yaml(root / "apps" / "web", web_sections)

    write_source_file(root / "apps" / "web" / "src" / "App.tsx",
                     "export const App = () => <div>Web App</div>;", "typescript")

    write_source_file(root / "apps" / "web" / "src" / "utils.ts",
                     "export function webUtil() { return 'web'; }", "typescript")

    write(root / "apps" / "web" / "docs" / "deployment.md", textwrap.dedent("""
        # Web App Deployment

        Deployment instructions for the web application.
        """).strip() + "\n")

    write(root / "apps" / "web" / "lg-cfg" / "docs" / "guide.tpl.md", "WEB GUIDE (no sections here)\n")
    write(root / "apps" / "web" / "lg-cfg" / "web-ctx.ctx.md", "# Guide\n\n${tpl:docs/guide}\n\n# Deployment\n\n${md:docs/deployment}\n")

    # === Child scope: libs/core ===
    core_sections = {
        "core-lib": {
            "extensions": [".py"],
            "python": {
                "skip_trivial_inits": True
            },
            "filters": {
                "mode": "allow",
                "allow": ["/core/**"]
            }
        },
        "core-api": {
            "extensions": [".py"],
            "python": {
                "strip_function_bodies": True
            },
            "filters": {
                "mode": "allow",
                "allow": ["/core/api/**"]
            }
        }
    }
    create_sections_yaml(root / "libs" / "core", core_sections)

    write_source_file(root / "libs" / "core" / "core" / "__init__.py", "", "python")

    write_source_file(root / "libs" / "core" / "core" / "processor.py",
                     "class Processor:\n    def process(self, data):\n        return data.upper()", "python")

    write_source_file(root / "libs" / "core" / "core" / "api" / "client.py",
                     "def get_client():\n    return CoreClient()\n\nclass CoreClient:\n    pass", "python")

    return root


@pytest.fixture
def fragments_project(tmp_path: Path) -> Path:
    """
    Creates a project with section fragments for testing *.sec.yaml files.

    Includes:
    - Base sections.yaml
    - Several fragments in different directories
    - Sections with canonical IDs
    """
    root = tmp_path

    # Base sections
    base_sections = {
        "main": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/main.py"]
            }
        }
    }
    create_sections_yaml(root, base_sections)

    # Fragment with single section (canonical ID = section name)
    fragment1 = {
        "database": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/db/**"]
            }
        }
    }
    create_section_fragment(root, "database", fragment1)

    # Fragment with multiple sections (canonical ID = prefix/section)
    fragment2 = {
        "auth": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/auth/**"]
            }
        },
        "permissions": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/permissions/**"]
            }
        }
    }
    create_section_fragment(root, "security", fragment2)

    # Fragment in subdirectory
    fragment3 = {
        "api-v1": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/api/v1/**"]
            }
        }
    }
    create_section_fragment(root, "api/v1", fragment3)

    # Create files for all sections
    write_source_file(root / "main.py", "print('main')", "python")
    write_source_file(root / "db" / "models.py", "class User: pass", "python")
    write_source_file(root / "auth" / "login.py", "def login(): pass", "python")
    write_source_file(root / "permissions" / "check.py", "def check(): pass", "python")
    write_source_file(root / "api" / "v1" / "handlers.py", "def handle(): pass", "python")

    return root


# ====================== Helpers for complex templates ======================

def create_nested_template_structure(root: Path) -> Dict[str, Path]:
    """
    Creates a structure of nested templates and contexts.

    Returns:
        Dictionary with paths to created files
    """
    paths = {}

    # Base templates
    paths["intro"] = create_template(root, "intro", """# Project Introduction

This is a generated introduction for the project.

## Key Features

- Modular architecture
- Extensible design
""", "tpl")

    paths["footer"] = create_template(root, "footer", """---

## Contact Information

For questions, contact the development team.
""", "tpl")

    # Composite templates
    paths["full-docs"] = create_template(root, "full-docs", """${tpl:intro}

## Source Code

${src}

## Documentation

${docs}

${tpl:footer}
""", "tpl")

    # Contexts
    paths["basic-context"] = create_template(root, "basic-context", """# Basic Project Context

${tpl:full-docs}

## Test Suite

${tests}
""", "ctx")

    paths["simple-context"] = create_template(root, "simple-context", """# Simple Context

${src}
${docs}
""", "ctx")

    return paths


def create_complex_federated_templates(root: Path) -> Dict[str, Path]:
    """
    Creates a complex structure of templates for a federated project.

    Returns:
        Dictionary with paths to created files
    """
    paths = {}

    # Root templates
    paths["project-overview"] = create_template(root, "project-overview", """# Project Overview

${overview}

## Web Application
${@apps/web:web-docs}

## Core Library
${@libs/core:core-lib}
""", "tpl")

    # Templates in child scopes
    paths["web-intro"] = create_template(root / "apps" / "web", "web-intro", """# Web Application

${web-src}

## Documentation
${web-docs}
""", "tpl")

    paths["core-api-docs"] = create_template(root / "libs" / "core", "api-docs", """# Core Library API

${core-api}
""", "tpl")

    # Contexts with cross-scope includes
    paths["full-stack-context"] = create_template(root, "full-stack", """# Full Stack Context

${tpl:project-overview}

## Detailed Web Implementation
${tpl@apps/web:web-intro}

## Core API Reference
${tpl@libs/core:api-docs}
""", "ctx")

    return paths


# ====================== Exports ======================

__all__ = [
    # Main fixtures
    "basic_project", "multilang_project", "federated_project", "fragments_project",

    # Helpers for creating files
    "write", "write_source_file", "create_sections_yaml", "create_section_fragment", "create_template",

    # Helpers for rendering
    "render_template", "make_run_options",

    # Pre-built configurations
    "get_basic_sections_config", "get_multilang_sections_config",

    # Helpers for complex structures
    "create_nested_template_structure", "create_complex_federated_templates"
]