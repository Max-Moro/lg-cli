"""
Tests for subdirectory section resolution bug.

When context is in lg-cfg/sub/_.ctx.md, placeholders like ${src} should resolve
to local lg-cfg/sub/src section instead of root-level lg-cfg/src section.

This bug causes list_tag_sets to return wrong tag-sets.
"""

from __future__ import annotations

import textwrap

import pytest

from tests.infrastructure import (
    write, create_mode_meta_section,
    ModeConfig, ModeSetConfig,
)


@pytest.fixture
def subdirectory_project(tmp_path):
    """
    Create a project structure with root and subdirectory sections.

    Structure:
    - lg-cfg/ai-interaction.sec.yaml (integration mode-set)
    - lg-cfg/tags.sec.yaml (tag-set "root-features")
    - lg-cfg/sections.yaml (src section extending tags)
    - lg-cfg/sub/tags.sec.yaml (tag-set "sub-features")
    - lg-cfg/sub/sections.yaml (src section extending tags)
    - lg-cfg/sub/_.ctx.md (context with ${src} placeholder)
    """
    root = tmp_path

    # Create integration mode-set at root level
    create_mode_meta_section(root, "ai-interaction", {
        "ai-interaction": ModeSetConfig(
            title="AI Interaction",
            modes={
                "ask": ModeConfig(title="Ask", runs={"com.test.provider": "--ask"}),
            }
        )
    })

    # Create root-level tags meta-section
    write(root / "lg-cfg" / "tags.sec.yaml", textwrap.dedent("""\
    tags:
      tag-sets:
        root-features:
          title: "Root Features"
          tags:
            feature-a:
              title: "Feature A"
    """))

    # Create root-level sections.yaml with src section
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
    src:
      extends: ["ai-interaction", "tags"]
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/**"
    """))

    # Create subdirectory tags meta-section (INSIDE sub/)
    write(root / "lg-cfg" / "sub" / "tags.sec.yaml", textwrap.dedent("""\
    tags:
      tag-sets:
        sub-features:
          title: "Sub Features"
          tags:
            feature-b:
              title: "Feature B"
    """))

    # Create subdirectory sections.yaml with src section
    write(root / "lg-cfg" / "sub" / "sections.yaml", textwrap.dedent("""\
    src:
      extends: ["ai-interaction", "tags"]
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/**"
    """))

    # Create subdirectory context with ${src} placeholder
    write(root / "lg-cfg" / "sub" / "_.ctx.md", textwrap.dedent("""\
    ---
    include: ["ai-interaction"]
    ---
    # Subdirectory Context
    ${src}
    """))

    # Create dummy source file
    write(root / "main.py", "x = 1\n")

    return root


class TestSubdirectorySectionResolution:
    """Tests for section resolution in subdirectories."""

    def test_list_tag_sets_includes_subdirectory_tags(self, subdirectory_project):
        """
        Test that list_tag_sets returns subdirectory tag-sets, not root-level ones.

        When context is in lg-cfg/sub/_.ctx.md and uses ${src},
        the section should resolve to lg-cfg/sub/sections.yaml,
        which extends "sub-tags" tag-set.

        Expected: "sub-features" is present, "root-features" is NOT present.
        """
        root = subdirectory_project

        from lg.adaptive.listing import list_tag_sets

        # Resolve tag-sets for subdirectory context
        result = list_tag_sets(root, "sub/_")
        tag_set_ids = {ts.id for ts in result.tag_sets}

        # Subdirectory tag-set should be present
        assert "sub-features" in tag_set_ids, \
            f"Expected 'sub-features' in {tag_set_ids}, but it's missing"

        # Root tag-set should NOT be present
        assert "root-features" not in tag_set_ids, \
            f"Expected 'root-features' NOT in {tag_set_ids}, but it's present"

    def test_section_collector_respects_current_directory(self, subdirectory_project):
        """
        Test that context resolver respects subdirectory when collecting sections.

        Uses create_context_resolver to verify section collection
        correctly resolves ${src} to local section.
        """
        root = subdirectory_project

        from lg.adaptive.context_resolver import create_context_resolver

        resolver, _, _ = create_context_resolver(root)

        # Resolve adaptive model for subdirectory context
        adaptive_data = resolver.resolve_for_context("sub/_")

        # Verify that the model contains sub-features tag-set
        tag_set_ids = {ts_id for ts_id in adaptive_data.model.tag_sets.keys()}

        assert "sub-features" in tag_set_ids, \
            f"Expected 'sub-features' in resolved model {tag_set_ids}, but it's missing"

        assert "root-features" not in tag_set_ids, \
            f"Expected 'root-features' NOT in resolved model {tag_set_ids}, but it's present"


__all__ = [
    "TestSubdirectorySectionResolution",
    "subdirectory_project",
]
