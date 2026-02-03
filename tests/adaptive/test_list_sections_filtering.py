"""
Integration tests for list sections with mode-sets/tag-sets filtering.

Tests the scenario where:
1. Context includes mode-sets via frontmatter
2. Section inherits only a subset via extends
3. IDE must use section's mode-sets, not context's
"""

from __future__ import annotations

import textwrap

import pytest

from tests.infrastructure import run_cli, jload, write


@pytest.fixture
def section_modes_project(tmp_path):
    """
    Project where section has its own mode-set, context adds others via frontmatter.

    Realistic scenario:
    - integration-modes.sec.yaml: integration mode-set (ai-interaction) with runs
    - dev-stage.sec.yaml: content mode-set for development workflow
    - feature-slices.sec.yaml: business mode-set for feature toggles (section-specific)
    - Section 'src' extends ONLY 'feature-slices'
    - Context includes 'integration-modes' + 'dev-stage' via frontmatter
    - Context gets 'feature-slices' through ${src} placeholder
    """
    root = tmp_path

    # Integration mode-set (has runs)
    write(root / "lg-cfg" / "integration-modes.sec.yaml", textwrap.dedent("""\
    integration-modes:
      mode-sets:
        ai-interaction:
          title: "AI Interaction"
          modes:
            ask:
              title: "Ask"
              runs:
                com.test.provider: "--mode ask"
            agent:
              title: "Agent"
              tags: ["agent"]
              runs:
                com.test.provider: "--mode agent"
    """))

    # Dev stage mode-set (content, no runs)
    write(root / "lg-cfg" / "dev-stage.sec.yaml", textwrap.dedent("""\
    dev-stage:
      mode-sets:
        dev-stage:
          title: "Development Stage"
          modes:
            development:
              title: "Development"
            testing:
              title: "Testing"
              tags: ["tests"]
            review:
              title: "Code Review"
              tags: ["review"]
              vcs_mode: "branch-changes"
    """))

    # Feature slices mode-set (business-specific, section owns this)
    write(root / "lg-cfg" / "feature-slices.sec.yaml", textwrap.dedent("""\
    feature-slices:
      mode-sets:
        payment-module:
          title: "Payment Module Slices"
          modes:
            all-features:
              title: "All Features"
            billing-only:
              title: "Billing Only"
              tags: ["billing"]
            checkout-only:
              title: "Checkout Only"
              tags: ["checkout"]
    """))

    # Section extending ONLY feature-slices (its own business mode-set)
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
    src:
      extends: ["feature-slices"]
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    """))

    # Context includes integration + dev-stage via frontmatter
    # Gets feature-slices (payment-module) through ${src} placeholder
    write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
    ---
    include: ["integration-modes", "dev-stage"]
    ---
    # Test Context
    ${src}
    """))

    # Source file
    write(root / "src" / "main.py", "def main(): pass\n")

    return root


class TestListSectionsFiltering:
    """Tests for list sections with mode-sets/tag-sets filtering."""

    def test_context_has_more_mode_sets_than_section(self, section_modes_project, monkeypatch):
        """Context includes mode-sets that section doesn't inherit."""
        root = section_modes_project
        monkeypatch.chdir(root)

        # Get mode-sets for context
        ctx_result = run_cli(root, "list", "mode-sets",
                             "--context", "test",
                             "--provider", "com.test.provider")
        assert ctx_result.returncode == 0
        ctx_data = jload(ctx_result.stdout)

        ctx_mode_set_ids = {ms["id"] for ms in ctx_data["mode-sets"]}

        # Context should have three mode-sets: ai-interaction, dev-stage, payment-module
        assert "ai-interaction" in ctx_mode_set_ids
        assert "dev-stage" in ctx_mode_set_ids
        assert "payment-module" in ctx_mode_set_ids

        # Get sections for context
        sec_result = run_cli(root, "list", "sections", "--context", "test")
        assert sec_result.returncode == 0
        sec_data = jload(sec_result.stdout)

        # Find src section
        src_section = next(s for s in sec_data["sections"] if s["name"] == "src")
        src_mode_set_ids = {ms["id"] for ms in src_section["mode-sets"]}

        # Section should have only ONE mode-set (payment-module)
        # It does NOT have ai-interaction or dev-stage from the context
        assert "payment-module" in src_mode_set_ids
        assert "ai-interaction" not in src_mode_set_ids
        assert "dev-stage" not in src_mode_set_ids

    def test_report_section_with_unsupported_mode_fails(self, section_modes_project, monkeypatch):
        """Using mode-set from context that section doesn't support should fail."""
        root = section_modes_project
        monkeypatch.chdir(root)

        # Try to use dev-stage mode (from frontmatter, section doesn't extend it)
        result = run_cli(root, "report", "sec:src",
                         "--mode", "dev-stage:testing")

        assert result.returncode == 2
        assert "Unknown mode set 'dev-stage'" in result.stderr

    def test_report_section_with_supported_mode_succeeds(self, section_modes_project, monkeypatch):
        """Using mode-set that section supports should succeed."""
        root = section_modes_project
        monkeypatch.chdir(root)

        # Use payment-module mode (section's own mode-set)
        result = run_cli(root, "report", "sec:src",
                         "--mode", "payment-module:billing-only")

        assert result.returncode == 0
        data = jload(result.stdout)
        assert data["target"] == "sec:src"
        assert len(data["files"]) > 0

    def test_ide_workflow_intersection(self, section_modes_project, monkeypatch):
        """
        Simulate IDE workflow: filter context modes by section's supported modes.

        This is the key test case: IDE gets modes from context, then filters
        by what section actually supports before calling report.

        Realistic scenario:
        - Context has: ai-interaction, dev-stage, payment-module
        - Section only supports: payment-module
        - IDE must filter context modes to intersection (payment-module only)
        """
        root = section_modes_project
        monkeypatch.chdir(root)

        # Step 1: IDE gets mode-sets for context
        ctx_result = run_cli(root, "list", "mode-sets",
                             "--context", "test",
                             "--provider", "com.test.provider")
        assert ctx_result.returncode == 0
        ctx_modes = jload(ctx_result.stdout)

        # Step 2: IDE gets sections with their mode-sets
        sec_result = run_cli(root, "list", "sections", "--context", "test")
        assert sec_result.returncode == 0
        sec_data = jload(sec_result.stdout)

        # Step 3: IDE picks a section and finds intersection
        src_section = next(s for s in sec_data["sections"] if s["name"] == "src")
        section_mode_set_ids = {ms["id"] for ms in src_section["mode-sets"]}

        # Filter context modes to only those supported by section
        valid_modes = []
        for ctx_ms in ctx_modes["mode-sets"]:
            if ctx_ms["id"] in section_mode_set_ids:
                # Pick first mode from each supported set
                if ctx_ms["modes"]:
                    valid_modes.append(f"{ctx_ms['id']}:{ctx_ms['modes'][0]['id']}")

        # Step 4: IDE calls report with filtered modes
        args = ["report", f"sec:{src_section['name']}"]
        for mode in valid_modes:
            args.extend(["--mode", mode])

        result = run_cli(root, *args)

        # Should succeed because we only used modes section supports
        assert result.returncode == 0
        data = jload(result.stdout)
        assert data["target"] == "sec:src"


class TestListSectionsBasic:
    """Basic tests for list sections command."""

    def test_list_sections_returns_mode_sets_and_tag_sets(self, section_modes_project, monkeypatch):
        """List sections should include mode-sets and tag-sets for each section."""
        root = section_modes_project
        monkeypatch.chdir(root)

        result = run_cli(root, "list", "sections")
        assert result.returncode == 0
        data = jload(result.stdout)

        assert "sections" in data
        sections = data["sections"]
        assert len(sections) >= 1

        # Each section should have required fields
        for section in sections:
            assert "name" in section
            assert "mode-sets" in section
            assert "tag-sets" in section

    def test_list_sections_with_context_filter(self, section_modes_project, monkeypatch):
        """List sections --context should return only sections used in context."""
        root = section_modes_project
        monkeypatch.chdir(root)

        result = run_cli(root, "list", "sections", "--context", "test")
        assert result.returncode == 0
        data = jload(result.stdout)

        section_names = [s["name"] for s in data["sections"]]
        assert "src" in section_names
