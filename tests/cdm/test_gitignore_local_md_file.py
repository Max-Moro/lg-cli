"""
Tests for gitignored local md files in root scope.

Verifies that md@self: placeholders work correctly when the target file
is covered by .gitignore (local-only files that shouldn't break rendering).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lg.filtering.manifest import _is_gitignored_section
from lg.filtering.model import FilterNode
from lg.git.gitignore import GitIgnoreService
from lg.section.model import SectionCfg
from tests.infrastructure import write


def _create_repo_with_gitignored_md(root: Path) -> Path:
    """
    Creates a simple repo with gitignored local md file in lg-cfg.

    Structure:
    root/
      .git/
      .gitignore              # ignores lg-cfg/agent/workspace-and-personal.md
      lg-cfg/
        sections.yaml
        main.ctx.md           # includes ${md@self:agent/workspace-and-personal}
        agent/
          index.tpl.md        # includes ${md@self:workspace-and-personal}
          workspace-and-personal.md  # this file is gitignored (may not exist)
    """
    # Root .git directory
    (root / ".git").mkdir(parents=True)

    # Root .gitignore - ignores local workspace file
    write(root / ".gitignore", textwrap.dedent("""
        # Local workspace settings
        lg-cfg/agent/workspace-and-personal.md
    """).strip() + "\n")

    # Root lg-cfg
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
        docs:
          extensions: [".md"]
          filters:
            mode: allow
            allow:
              - "/README.md"
    """).strip() + "\n")

    # Context that includes local docs via md@self placeholder
    write(root / "lg-cfg" / "main.ctx.md", textwrap.dedent("""
        # Main Context

        ${md@self:agent/workspace-and-personal}
    """).strip() + "\n")

    # Template that includes local md via relative path
    write(root / "lg-cfg" / "agent" / "index.tpl.md", textwrap.dedent("""
        # Agent Instructions

        ${md@self:workspace-and-personal}
    """).strip() + "\n")

    # README for docs section
    write(root / "README.md", "# Project README\n")

    return root


@pytest.fixture
def repo_with_gitignored_md(tmp_path: Path) -> Path:
    """Fixture creating repo with gitignored local md file."""
    return _create_repo_with_gitignored_md(tmp_path)


class TestGitignoreLocalMdFile:
    """Tests for gitignored local markdown files in root scope."""

    def test_gitignore_service_recognizes_lg_cfg_path(self, repo_with_gitignored_md: Path):
        """
        GitIgnoreService should recognize paths inside lg-cfg that are gitignored.
        """
        root = repo_with_gitignored_md

        gitignore_service = GitIgnoreService(root)

        # This path should be ignored
        assert gitignore_service.is_ignored("lg-cfg/agent/workspace-and-personal.md"), (
            "GitIgnoreService should recognize lg-cfg/agent/workspace-and-personal.md as ignored"
        )

    def test_is_gitignored_section_for_virtual_md_section(self, repo_with_gitignored_md: Path):
        """
        _is_gitignored_section should return True for virtual section
        created from md@self: placeholder when file is in .gitignore.
        """
        root = repo_with_gitignored_md

        gitignore_service = GitIgnoreService(root)

        # Create a section config similar to what VirtualSectionFactory creates
        # for md@self:agent/workspace-and-personal
        section_cfg = SectionCfg(
            extensions=[".md"],
            filters=FilterNode(
                mode="allow",
                allow=["/lg-cfg/agent/workspace-and-personal.md"]
            )
        )

        # scope_rel is empty for root scope
        result = _is_gitignored_section(section_cfg, gitignore_service, scope_rel="")

        assert result is True, (
            "Section with allow pattern /lg-cfg/agent/workspace-and-personal.md "
            "should be recognized as gitignored when file is in .gitignore"
        )

    def test_is_gitignored_section_for_non_gitignored_path(self, repo_with_gitignored_md: Path):
        """
        _is_gitignored_section should return False for paths not in .gitignore.
        """
        root = repo_with_gitignored_md

        gitignore_service = GitIgnoreService(root)

        # Section for non-gitignored file
        section_cfg = SectionCfg(
            extensions=[".md"],
            filters=FilterNode(
                mode="allow",
                allow=["/README.md"]
            )
        )

        result = _is_gitignored_section(section_cfg, gitignore_service, scope_rel="")

        assert result is False, (
            "Section with allow pattern /README.md should NOT be recognized as gitignored"
        )

    def test_missing_gitignored_local_md_does_not_raise(self, repo_with_gitignored_md: Path):
        """
        Rendering context that includes gitignored local md file
        should NOT raise RuntimeError when file is missing.
        """
        from tests.infrastructure import make_engine

        root = repo_with_gitignored_md

        # DO NOT create the gitignored file
        # lg-cfg/agent/workspace-and-personal.md does not exist

        engine = make_engine(root)

        # This should NOT raise RuntimeError about missing markdown files
        try:
            result = engine.render_context("main")
            # If we get here, the test passes - no RuntimeError was raised
            assert "Main Context" in result
        except RuntimeError as e:
            if "No markdown files found" in str(e):
                pytest.fail(
                    f"RuntimeError raised for missing gitignored file: {e}. "
                    "This indicates gitignore check is not working correctly."
                )
            raise

    def test_existing_gitignored_local_md_is_included(self, repo_with_gitignored_md: Path):
        """
        When gitignored local md file exists, it should be included in rendering.
        """
        from tests.infrastructure import make_engine

        root = repo_with_gitignored_md

        # Create the gitignored file
        write(
            root / "lg-cfg" / "agent" / "workspace-and-personal.md",
            "## Local Workspace Settings\n\nPersonal configuration notes.\n"
        )

        engine = make_engine(root)

        result = engine.render_context("main")

        assert "Main Context" in result
        assert "Local Workspace Settings" in result, (
            "Content from existing gitignored local file should be included"
        )

    def test_nested_template_with_gitignored_md(self, repo_with_gitignored_md: Path):
        """
        Test nested template scenario: context includes tpl which includes md@self.

        This reproduces the real-world case:
        - common.ctx.md includes ${tpl:agent/index}
        - agent/index.tpl.md includes ${md@self:workspace-and-personal}
        - lg-cfg/agent/workspace-and-personal.md is gitignored
        """
        from tests.infrastructure import make_engine

        root = repo_with_gitignored_md

        # Update main.ctx.md to use a template instead of direct md placeholder
        write(root / "lg-cfg" / "main.ctx.md", textwrap.dedent("""
            # Main Context

            ${tpl:agent/index}
        """).strip() + "\n")

        # DO NOT create the gitignored file
        # lg-cfg/agent/workspace-and-personal.md does not exist

        engine = make_engine(root)

        # This should NOT raise RuntimeError about missing markdown files
        try:
            result = engine.render_context("main")
            # If we get here, the test passes
            assert "Agent Instructions" in result
        except RuntimeError as e:
            if "No markdown files found" in str(e):
                pytest.fail(
                    f"RuntimeError raised for missing gitignored file in nested template: {e}. "
                    "This indicates gitignore check fails when processing through nested templates."
                )
            raise
