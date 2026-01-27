"""
Test infrastructure for adaptive subsystem tests.

Provides fixtures for testing extends resolution, context resolution,
provider filtering, and listing API.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tests.infrastructure import (
    write,
    create_mode_meta_section, create_tag_meta_section,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig,
)


@pytest.fixture
def extends_project(tmp_path: Path) -> Path:
    """
    Project with section inheritance chains.

    Structure:
    - base-modes.sec.yaml: meta-section with integration mode-set (ai-interaction)
    - extra-modes.sec.yaml: meta-section with content mode-set (dev-stage)
    - tags.sec.yaml: meta-section with tag-sets
    - sections.yaml: section extending all three meta-sections
    """
    root = tmp_path

    # Base integration mode-set (has runs → integration)
    create_mode_meta_section(root, "base-modes", {
        "ai-interaction": ModeSetConfig(
            title="AI Interaction",
            modes={
                "ask": ModeConfig(
                    title="Ask",
                    runs={"com.test.provider": "--mode ask"},
                ),
                "agent": ModeConfig(
                    title="Agent",
                    tags=["agent"],
                    runs={"com.test.provider": "--mode agent"},
                ),
            }
        )
    })

    # Content mode-set (no runs → content)
    create_mode_meta_section(root, "extra-modes", {
        "dev-stage": ModeSetConfig(
            title="Dev Stage",
            modes={
                "planning": ModeConfig(title="Planning", tags=["docs"]),
                "development": ModeConfig(title="Development"),
            }
        )
    })

    # Tag-sets
    create_tag_meta_section(root, "tags", {
        "language": TagSetConfig(
            title="Languages",
            tags={
                "python": TagConfig(title="Python"),
                "typescript": TagConfig(title="TypeScript"),
            }
        )
    })

    # Regular section extending all meta-sections
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
    src:
      extends: ["base-modes", "extra-modes", "tags"]
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    """))

    # Source files
    write(root / "src" / "main.py", "def main(): pass\n")

    return root


@pytest.fixture
def multi_provider_project(tmp_path: Path) -> Path:
    """
    Project with multiple providers in runs.

    Integration mode-set supports three providers with varying coverage:
    - com.test.provider.cli: supports ask, agent, plan
    - com.other.provider.ext: supports ask, agent
    - com.partial.provider.cli: supports only ask
    """
    root = tmp_path

    create_mode_meta_section(root, "ai-interaction", {
        "ai-interaction": ModeSetConfig(
            title="AI Interaction",
            modes={
                "ask": ModeConfig(
                    title="Ask",
                    runs={
                        "com.test.provider.cli": "--mode ask",
                        "com.other.provider.ext": "action.ask",
                        "com.partial.provider.cli": "--ask",
                    },
                ),
                "agent": ModeConfig(
                    title="Agent",
                    tags=["agent"],
                    runs={
                        "com.test.provider.cli": "--mode agent",
                        "com.other.provider.ext": "action.agent",
                    },
                ),
                "plan": ModeConfig(
                    title="Plan",
                    tags=["agent", "plan"],
                    runs={
                        "com.test.provider.cli": "--mode plan",
                    },
                ),
            }
        )
    })

    # Content mode-set (no runs)
    create_mode_meta_section(root, "dev-stage", {
        "dev-stage": ModeSetConfig(
            title="Dev Stage",
            modes={
                "development": ModeConfig(title="Development"),
                "review": ModeConfig(title="Review", tags=["review"]),
            }
        )
    })

    # Section without extends (provider filtering uses frontmatter only)
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
    src:
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    """))

    # Context with frontmatter
    write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
    ---
    include: ["ai-interaction", "dev-stage"]
    ---
    # Test
    ${src}
    """))

    # Source files
    write(root / "src" / "main.py", "def main(): pass\n")

    return root
