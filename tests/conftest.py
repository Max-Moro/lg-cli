import textwrap
from pathlib import Path

import pytest

from tests.infrastructure import write, write_context, create_integration_mode_section


@pytest.fixture
def tmpproj(tmp_path: Path):
    """Minimal project schema: lg-cfg/sections.yaml + ctx/tpl in lg-cfg/ root."""
    root = tmp_path

    # Create integration mode section for adaptive system
    create_integration_mode_section(root)

    # sections.yaml with two sections (with extends for adaptive support)
    write(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent("""
        all:
          extends: ["ai-interaction"]
          extensions: [".md", ".py"]
          markdown:
            max_heading_level: 2
          targets:
            - match: "/pkg/**.py"
              python:
                strip_function_bodies: true
        docs:
          extends: ["ai-interaction"]
          extensions: [".md"]
          markdown:
            max_heading_level: 3
          targets:
            - match: ["/docs/**.md"]
        """).strip() + "\n",
    )
    # template and two contexts
    write(root / "lg-cfg" / "a.tpl.md", "Intro\n\n${docs}\n")
    write_context(root, "a", "Intro (ctx)\n\n${docs}\n")
    write_context(root, "b", "X ${tpl:a} Y ${all}\n")
    return root

@pytest.fixture(autouse=True)
def _allow_migrations_without_git(monkeypatch):
    # safe for unit tests: in production the variable is not set
    monkeypatch.setenv("LG_MIGRATE_ALLOW_NO_GIT", "1")