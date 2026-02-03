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
    Project where section supports fewer mode-sets than context.

    Structure:
    - integration-modes.sec.yaml: integration mode-set (ai-interaction)
    - content-modes-a.sec.yaml: content mode-set that section DOES extend
    - content-modes-b.sec.yaml: content mode-set that section does NOT extend
    - sections.yaml: section extending only integration + content-a
    - test.ctx.md: context including ALL three via frontmatter
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

    # Content mode-set A (section WILL extend this)
    write(root / "lg-cfg" / "content-modes-a.sec.yaml", textwrap.dedent("""\
    content-modes-a:
      mode-sets:
        dev-stage:
          title: "Dev Stage"
          modes:
            development:
              title: "Development"
            testing:
              title: "Testing"
              tags: ["tests"]
    """))

    # Content mode-set B (section will NOT extend this)
    write(root / "lg-cfg" / "content-modes-b.sec.yaml", textwrap.dedent("""\
    content-modes-b:
      mode-sets:
        review-workflow:
          title: "Review Workflow"
          modes:
            self-review:
              title: "Self Review"
            peer-review:
              title: "Peer Review"
              tags: ["review"]
    """))

    # Section extending only integration + content-a (NOT content-b)
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""\
    src:
      extends: ["integration-modes", "content-modes-a"]
      extensions: [".py"]
      filters:
        mode: allow
        allow:
          - "/src/**"
    """))

    # Context includes ALL mode-sets via frontmatter
    write(root / "lg-cfg" / "test.ctx.md", textwrap.dedent("""\
    ---
    include: ["integration-modes", "content-modes-a", "content-modes-b"]
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

        # Context should have ALL three mode-sets
        assert "ai-interaction" in ctx_mode_set_ids
        assert "dev-stage" in ctx_mode_set_ids
        assert "review-workflow" in ctx_mode_set_ids

        # Get sections for context
        sec_result = run_cli(root, "list", "sections", "--context", "test")
        assert sec_result.returncode == 0
        sec_data = jload(sec_result.stdout)

        # Find src section
        src_section = next(s for s in sec_data["sections"] if s["name"] == "src")
        src_mode_set_ids = {ms["id"] for ms in src_section["mode-sets"]}

        # Section should have only TWO mode-sets (not review-workflow)
        assert "ai-interaction" in src_mode_set_ids
        assert "dev-stage" in src_mode_set_ids
        assert "review-workflow" not in src_mode_set_ids

    def test_report_section_with_unsupported_mode_fails(self, section_modes_project, monkeypatch):
        """Using mode-set from context that section doesn't support should fail."""
        root = section_modes_project
        monkeypatch.chdir(root)

        # Try to use review-workflow mode (section doesn't extend content-modes-b)
        result = run_cli(root, "report", "sec:src",
                         "--mode", "review-workflow:self-review")

        assert result.returncode == 2
        assert "Unknown mode set 'review-workflow'" in result.stderr

    def test_report_section_with_supported_mode_succeeds(self, section_modes_project, monkeypatch):
        """Using mode-set that section supports should succeed."""
        root = section_modes_project
        monkeypatch.chdir(root)

        # Use dev-stage mode (section extends content-modes-a)
        result = run_cli(root, "report", "sec:src",
                         "--mode", "ai-interaction:agent",
                         "--mode", "dev-stage:testing")

        assert result.returncode == 0
        data = jload(result.stdout)
        assert data["target"] == "sec:src"
        assert len(data["files"]) > 0

    def test_ide_workflow_intersection(self, section_modes_project, monkeypatch):
        """
        Simulate IDE workflow: filter context modes by section's supported modes.

        This is the key test case: IDE gets modes from context, then filters
        by what section actually supports before calling report.
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
