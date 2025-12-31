"""
Tests for recursive .gitignore handling in federated repositories.

Verifies that GitIgnoreService correctly handles nested .gitignore files
in federated repository scenarios (e.g., git submodules).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lg.filtering.manifest import build_section_manifest
from lg.template.context import TemplateContext
from lg.addressing.types import ResolvedSection
from lg.section import SectionLocation
from lg.types import SectionManifest
from tests.infrastructure import make_run_context
from tests.infrastructure import write, load_sections


def _create_federated_with_gitignore(root: Path) -> Path:
    """
    Creates a federated repo with subproject that has gitignored local docs.

    Structure:
    root/
      .git/
      .gitignore              # does NOT ignore lg-cfg/ at root level
      lg-cfg/
        sections.yaml
        main.ctx.md           # includes ${md@subproject:personal/notes}
      subproject/
        .git/                 # simulates git submodule
        .gitignore            # ignores lg-cfg/personal/
        lg-cfg/
          sections.yaml       # section 'local-docs' with allow: /personal/
          personal/
            notes.md          # this file is gitignored
        src/
          app.py
    """
    # Root .git directory
    (root / ".git").mkdir(parents=True)

    # Root .gitignore - does NOT ignore lg-cfg/
    write(root / ".gitignore", "*.log\n__pycache__/\n")

    # Root lg-cfg with context that includes from subproject
    write(root / "lg-cfg" / "sections.yaml", textwrap.dedent("""
        root-src:
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/subproject/src/**"
    """).strip() + "\n")

    # Context that includes local docs from subproject via md@ placeholder
    write(root / "lg-cfg" / "main.ctx.md", textwrap.dedent("""
        # Main Context

        ## Subproject Documentation

        ${md@subproject:personal/notes}

        ## Source Code

        ${root-src}
    """).strip() + "\n")

    # Subproject with its own .git (simulating submodule)
    subproject = root / "subproject"
    (subproject / ".git").mkdir(parents=True)

    # Subproject .gitignore - ignores lg-cfg/personal/
    write(subproject / ".gitignore", "lg-cfg/personal/\n")

    # Subproject lg-cfg with section for local docs
    write(subproject / "lg-cfg" / "sections.yaml", textwrap.dedent("""
        local-docs:
          extensions: [".md"]
          filters:
            mode: allow
            allow:
              - "/lg-cfg/personal/**"

        subproject-src:
          extensions: [".py"]
          filters:
            mode: allow
            allow:
              - "/src/**"
    """).strip() + "\n")

    # Subproject source files (not gitignored)
    write(subproject / "src" / "app.py", "def main():\n    pass\n")

    return root


@pytest.fixture
def federated_with_gitignore(tmp_path: Path) -> Path:
    """Fixture creating federated repo with gitignored local docs in subproject."""
    return _create_federated_with_gitignore(tmp_path)


def _build_manifest_for_section(
    root: Path,
    section_name: str,
    scope_rel: str = "",
) -> SectionManifest:
    """Helper to build manifest for a section."""
    rc = make_run_context(root)
    template_ctx = TemplateContext(rc)

    if scope_rel:
        scope_dir = (root / scope_rel).resolve()
    else:
        scope_dir = root

    sections = load_sections(scope_dir)
    section_cfg = sections.get(section_name)

    if not section_cfg:
        available = list(sections.keys())
        raise RuntimeError(
            f"Section '{section_name}' not found in {scope_dir}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    resolved = ResolvedSection(
        scope_dir=scope_dir,
        scope_rel=scope_rel,
        location=SectionLocation(file_path=Path("test"), local_name=section_name),
        section_config=section_cfg,
        name=section_name
    )

    return build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=root,
        vcs=rc.vcs,
        gitignore_service=rc.gitignore,
        vcs_mode="all"
    )


class TestRecursiveGitignoreInFederatedRepo:
    """Tests for recursive .gitignore handling in federated repositories."""

    def test_is_local_files_true_for_gitignored_section_in_subproject(
        self, federated_with_gitignore: Path
    ):
        """
        Section with allow patterns covered by subproject's .gitignore
        should have is_local_files=True when accessed from root.

        This verifies that GitIgnoreService correctly reads nested .gitignore
        files (subproject/.gitignore) when checking patterns.
        """
        root = federated_with_gitignore

        # Create the gitignored file so manifest can be built
        write(root / "subproject" / "lg-cfg" / "personal" / "notes.md", "Personal notes\n")

        # Build manifest for local-docs section from subproject scope
        manifest = _build_manifest_for_section(root, "local-docs", "subproject")

        # Key assertion: is_local_files should be True because the section's
        # allow patterns (/lg-cfg/personal/**) are covered by subproject's .gitignore
        assert manifest.is_local_files is True, (
            "Section with gitignored allow patterns should have is_local_files=True. "
            "This indicates GitIgnoreService correctly processed subproject/.gitignore"
        )

    def test_is_local_files_false_for_non_gitignored_section(
        self, federated_with_gitignore: Path
    ):
        """
        Section with allow patterns NOT covered by .gitignore
        should have is_local_files=False.
        """
        root = federated_with_gitignore

        # Build manifest for subproject-src section (not gitignored)
        manifest = _build_manifest_for_section(root, "subproject-src", "subproject")

        # This section's allow patterns (/src/**) are not gitignored
        assert manifest.is_local_files is False

    def test_missing_gitignored_file_does_not_break_manifest(
        self, federated_with_gitignore: Path
    ):
        """
        When gitignored local file is missing (not cloned/created),
        manifest building should succeed with empty files list.

        This simulates a colleague cloning the repo without the local docs.
        """
        root = federated_with_gitignore

        # DO NOT create the gitignored file - simulating missing local docs
        # subproject/lg-cfg/personal/notes.md does not exist

        # Build manifest for local-docs section
        manifest = _build_manifest_for_section(root, "local-docs", "subproject")

        # Manifest should build successfully with is_local_files=True
        assert manifest.is_local_files is True

        # Files list should be empty (file doesn't exist)
        assert len(manifest.files) == 0

    def test_recursive_gitignore_respects_git_boundaries(
        self, federated_with_gitignore: Path
    ):
        """
        Root .gitignore rules should not affect subproject files,
        and subproject .gitignore should not leak to root.

        Each .git directory creates a boundary for .gitignore scope.
        """
        root = federated_with_gitignore

        # Create files in both scopes
        write(root / "subproject" / "lg-cfg" / "personal" / "notes.md", "Notes\n")
        write(root / "subproject" / "src" / "app.py", "# app\n")

        # Root's .gitignore has *.log - should not affect subproject
        write(root / "subproject" / "src" / "debug.log", "log content\n")

        # Build manifest for root-src (includes subproject/src/**)
        manifest = _build_manifest_for_section(root, "root-src", "")

        rels = [f.rel_path for f in manifest.files]

        # .py files should be included
        assert "subproject/src/app.py" in rels

        # .log files should be excluded by root's .gitignore
        assert "subproject/src/debug.log" not in rels

    def test_full_rendering_with_missing_local_docs(
        self, federated_with_gitignore: Path
    ):
        """
        Full rendering of context that includes gitignored local docs
        should not raise RuntimeError when files are missing.

        This is the end-to-end test for the federated scenario.
        """
        from tests.infrastructure import make_engine

        root = federated_with_gitignore

        # DO NOT create the gitignored file
        # subproject/lg-cfg/personal/notes.md does not exist

        # Create engine with correct root path
        engine = make_engine(root)

        # This should NOT raise RuntimeError about missing markdown files
        # because the section has is_local_files=True
        try:
            result = engine.render_context("main")
            # If we get here, the test passes - no RuntimeError was raised
            assert "Main Context" in result
        except RuntimeError as e:
            if "No markdown files found" in str(e):
                pytest.fail(
                    f"RuntimeError raised for missing gitignored file: {e}. "
                    "This indicates recursive .gitignore is not working correctly - "
                    "is_local_files flag was not set for the gitignored section."
                )
            raise
