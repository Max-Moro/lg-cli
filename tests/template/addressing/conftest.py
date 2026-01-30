"""
Fixtures for addressing system integration tests.

Reproduces real-world scenario from vscode/lg-cfg/adaptability/_.ctx.md
"""

from __future__ import annotations

import pytest
from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.section import SectionService
from lg.addressing import AddressingContext
from lg.version import tool_version


@pytest.fixture
def multi_scope_project(tmp_path: Path) -> Path:
    """
    Creates project structure mimicking the real bug scenario.

    Structure:
        root/                       # Parent scope (like lg/)
        ├── lg-cfg/
        │   ├── sections.yaml
        │   └── adaptability/
        │       └── architecture-adaptive-ide.md
        │
        ├── vscode/                 # Child scope (current working dir)
        │   └── lg-cfg/
        │       ├── sections.yaml
        │       └── adaptability/
        │           └── _.ctx.md    # Context with @.. references
        │
        └── cli/                    # Sibling scope
            └── lg-cfg/
                ├── sections.yaml
                └── docs/
                    └── en/
                        └── adaptability.md
    """
    root = tmp_path / "root"

    # === Parent scope (root/lg-cfg/) ===
    root_cfg = root / "lg-cfg"
    root_cfg.mkdir(parents=True)

    (root_cfg / "sections.yaml").write_text(
        "docs:\n"
        "  extensions: ['.md']\n"
        "  filters:\n"
        "    mode: allow\n"
        "    allow:\n"
        "      - '/adaptability/'\n",
        encoding="utf-8"
    )

    adaptability_dir = root_cfg / "adaptability"
    adaptability_dir.mkdir()
    (adaptability_dir / "architecture-adaptive-ide.md").write_text(
        "# Architecture from PARENT scope\n\n"
        "This is the architecture document from parent scope.\n",
        encoding="utf-8"
    )

    # === Child scope (root/vscode/lg-cfg/) ===
    vscode_cfg = root / "vscode" / "lg-cfg"
    vscode_cfg.mkdir(parents=True)

    (vscode_cfg / "sections.yaml").write_text(
        "src:\n"
        "  extensions: ['.ts']\n"
        "  filters:\n"
        "    mode: allow\n"
        "    allow:\n"
        "      - '/src/'\n",
        encoding="utf-8"
    )

    vscode_adaptability = vscode_cfg / "adaptability"
    vscode_adaptability.mkdir()

    # Context that uses parent scope references
    (vscode_adaptability / "_.ctx.md").write_text(
        "# Adaptability Context\n\n"
        "## Architecture from parent scope\n\n"
        "${md@..:adaptability/architecture-adaptive-ide}\n\n"
        "## CLI docs from sibling scope\n\n"
        "${md@../cli:docs/en/adaptability}\n",
        encoding="utf-8"
    )

    # Also create a simpler test context for current_dir reset bug
    (vscode_adaptability / "simple.ctx.md").write_text(
        "# Simple test\n\n"
        "${md@..:adaptability/architecture-adaptive-ide}\n",
        encoding="utf-8"
    )

    # === Sibling scope (root/cli/lg-cfg/) ===
    cli_cfg = root / "cli" / "lg-cfg"
    cli_cfg.mkdir(parents=True)

    (cli_cfg / "sections.yaml").write_text(
        "docs:\n"
        "  extensions: ['.md']\n"
        "  filters:\n"
        "    mode: allow\n"
        "    allow:\n"
        "      - '/docs/'\n",
        encoding="utf-8"
    )

    cli_docs = cli_cfg / "docs" / "en"
    cli_docs.mkdir(parents=True)
    (cli_docs / "adaptability.md").write_text(
        "# CLI docs from SIBLING scope\n\n"
        "This is from the CLI sibling scope.\n",
        encoding="utf-8"
    )

    return root


@pytest.fixture
def vscode_scope_root(multi_scope_project: Path) -> Path:
    """Returns path to vscode scope (child scope)."""
    return multi_scope_project / "vscode"


@pytest.fixture
def addressing_context_in_vscode(vscode_scope_root: Path, multi_scope_project: Path) -> AddressingContext:
    """
    Creates AddressingContext as if running from vscode/ directory.

    This simulates the real scenario where:
    - repo_root = root/ (parent of vscode/)
    - initial_cfg_root = vscode/lg-cfg/
    """
    cache = Cache(multi_scope_project, enabled=False, fresh=True, tool_version=tool_version())
    section_service = SectionService(multi_scope_project, cache)

    return AddressingContext(
        repo_root=multi_scope_project,
        initial_cfg_root=vscode_scope_root / "lg-cfg",
        section_service=section_service
    )
