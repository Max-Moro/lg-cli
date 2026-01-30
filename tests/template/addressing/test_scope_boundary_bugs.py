"""
Integration tests for scope boundary handling.

Tests for parent directory references (@.., @../sibling) in origin
and current_dir reset behavior when transitioning between scopes.

These tests validate the fix for bugs discovered in real usage:
    vscode/lg-cfg/adaptability/_.ctx.md contains:
    - ${md@..:adaptability/architecture-adaptive-ide}
    - ${md@../cli:docs/en/adaptability}
"""

from __future__ import annotations

import pytest
from pathlib import Path

from lg.addressing import AddressingContext
from lg.addressing.types import ResourceConfig, ResolvedFile
from lg.addressing.errors import PathResolutionError, ScopeNotFoundError


# Resource config for markdown files with origin (md@origin:path)
# Files are INSIDE lg-cfg/ of target scope, so NO resolve_outside_cfg
MD_WITH_ORIGIN_CFG = ResourceConfig(
    kind="md",
    extension=".md",
    strip_md_syntax=True,
    # resolve_outside_cfg=False (default) — files inside lg-cfg/
)

# Resource config for markdown files without origin (md:path)
# Files are OUTSIDE lg-cfg/, relative to scope root
MD_OUTSIDE_CFG = ResourceConfig(
    kind="md",
    extension=".md",
    strip_md_syntax=True,
    resolve_outside_cfg=True,
)


class TestParentDirectoryInOrigin:
    """
    Tests for parent directory references in origin.

    Verifies that:
    - @.. resolves to parent scope
    - @../sibling resolves to sibling scope
    """

    def test_parent_scope_reference_works(
        self,
        addressing_context_in_vscode: AddressingContext,
        vscode_scope_root: Path,
        multi_scope_project: Path,
    ):
        """
        Test that @.. in origin correctly resolves to parent scope.

        Scenario:
        - Current scope: vscode/lg-cfg/
        - Reference: @..:adaptability/architecture-adaptive-ide
        - Expected: resolves to root/lg-cfg/adaptability/architecture-adaptive-ide.md

        Note: md@origin:path resolves files INSIDE lg-cfg/ of target scope.
        """
        ctx = addressing_context_in_vscode

        # Push context as if processing vscode/lg-cfg/adaptability/_.ctx.md
        ctx.push(vscode_scope_root / "lg-cfg" / "adaptability" / "_.ctx.md")
        assert ctx.current_directory == "adaptability"

        # Resolve with @ prefix - uses MD_WITH_ORIGIN_CFG (inside lg-cfg/)
        result = ctx.resolve("@..:adaptability/architecture-adaptive-ide", MD_WITH_ORIGIN_CFG)

        # Verify result type
        assert isinstance(result, ResolvedFile)

        # Verify scope resolved to parent (root)
        assert result.scope_dir == multi_scope_project
        assert result.scope_rel == ""

        # Verify resource path points to correct file INSIDE lg-cfg/ of parent scope
        expected_path = multi_scope_project / "lg-cfg" / "adaptability" / "architecture-adaptive-ide.md"
        assert result.resource_path == expected_path

    def test_sibling_scope_reference_works(
        self,
        addressing_context_in_vscode: AddressingContext,
        vscode_scope_root: Path,
        multi_scope_project: Path,
    ):
        """
        Test that @../sibling in origin correctly resolves to sibling scope.

        Scenario:
        - Current scope: vscode/lg-cfg/
        - Reference: @../cli:docs/en/adaptability
        - Expected: resolves to root/cli/lg-cfg/docs/en/adaptability.md

        Note: md@origin:path resolves files INSIDE lg-cfg/ of target scope.
        """
        ctx = addressing_context_in_vscode

        # Push context as if processing vscode/lg-cfg/adaptability/_.ctx.md
        ctx.push(vscode_scope_root / "lg-cfg" / "adaptability" / "_.ctx.md")

        # Resolve with @ prefix - uses MD_WITH_ORIGIN_CFG (inside lg-cfg/)
        result = ctx.resolve("@../cli:docs/en/adaptability", MD_WITH_ORIGIN_CFG)

        # Verify result type
        assert isinstance(result, ResolvedFile)

        # Verify scope resolved to sibling (cli/)
        expected_scope = multi_scope_project / "cli"
        assert result.scope_dir == expected_scope
        assert result.scope_rel == "cli"

        # Verify resource path points to correct file INSIDE lg-cfg/ of sibling scope
        expected_path = expected_scope / "lg-cfg" / "docs" / "en" / "adaptability.md"
        assert result.resource_path == expected_path

    def test_path_without_at_is_local(
        self,
        addressing_context_in_vscode: AddressingContext,
        vscode_scope_root: Path,
    ):
        """
        Test that paths without @ are resolved locally within current scope.

        Paths like '../cli:path' (without @) should be treated as local paths
        and may fail if they try to escape the scope boundary.
        """
        ctx = addressing_context_in_vscode
        ctx.push(vscode_scope_root / "lg-cfg" / "adaptability" / "_.ctx.md")

        # Without @ prefix, the colon is part of the path, not origin separator
        # This should fail because it tries to escape scope boundary
        with pytest.raises(PathResolutionError) as exc_info:
            ctx.resolve("../cli:docs/en/adaptability", MD_OUTSIDE_CFG)

        assert "escape" in str(exc_info.value).lower()


class TestCurrentDirResetOnScopeTransition:
    """
    Tests for current_dir reset behavior when transitioning between scopes.

    Verifies that:
    - current_dir resets to "" when entering a new scope
    - Paths in new scope resolve from scope root, not old current_dir
    """

    def test_current_dir_resets_on_scope_change(
        self,
        addressing_context_in_vscode: AddressingContext,
        vscode_scope_root: Path,
        multi_scope_project: Path,
    ):
        """
        Test that current_dir resets when changing scope via push with new_origin.

        Scenario:
        1. Start in vscode/lg-cfg/adaptability/ (current_dir = "adaptability")
        2. Transition to parent scope via push with new_origin=".."
        3. current_dir should become "" in new scope
        """
        ctx = addressing_context_in_vscode

        # Step 1: Push file context from nested directory
        template_path = vscode_scope_root / "lg-cfg" / "adaptability" / "_.ctx.md"
        ctx.push(template_path)

        # Verify we're in nested directory
        assert ctx.current_directory == "adaptability"

        # Step 2: Simulate scope transition to parent
        parent_cfg_root = multi_scope_project / "lg-cfg"
        ctx.push(parent_cfg_root / "some_file.md", new_origin="..")

        # Step 3: Verify current_dir was reset
        assert ctx.current_directory == "", \
            f"current_dir should be '' after scope transition, got '{ctx.current_directory}'"

        # Clean up
        ctx.pop()
        ctx.pop()


class TestIntegrationWithRealContextFile:
    """
    Integration tests that render actual context files with cross-scope references.
    """

    def test_render_context_with_parent_references(
        self,
        multi_scope_project: Path,
        vscode_scope_root: Path,
    ):
        """
        Full integration test rendering _.ctx.md from vscode scope.

        This test renders the context file that contains:
        - ${md@..:adaptability/architecture-adaptive-ide}
        - ${md@../cli:docs/en/adaptability}
        """
        import os

        # Change to vscode directory (simulating real usage)
        original_cwd = os.getcwd()
        try:
            os.chdir(vscode_scope_root)

            from lg.engine import run_render
            from lg.types import RunOptions

            options = RunOptions(
                tokenizer_lib="tiktoken",
                encoder="cl100k_base",
                ctx_limit=128000,
            )

            # This should now work after the fix
            result = run_render("adaptability/_", options)

            # Verify content from parent scope is included
            # Note: H1 headers are stripped by default, so we check for body content
            assert "architecture document from parent scope" in result, \
                f"Expected content from parent scope not found in result:\n{result}"

            # Verify content from sibling scope is included
            assert "from the CLI sibling scope" in result, \
                f"Expected content from sibling scope not found in result:\n{result}"

        finally:
            os.chdir(original_cwd)

    def test_render_fails_gracefully_for_missing_scope(
        self,
        multi_scope_project: Path,
        vscode_scope_root: Path,
    ):
        """
        Test that rendering fails gracefully when referenced scope doesn't exist.
        """
        import os

        # Create a context that references non-existent scope
        bad_ctx = vscode_scope_root / "lg-cfg" / "bad.ctx.md"
        bad_ctx.write_text(
            "# Bad reference\n${md@../nonexistent:some/file}\n",
            encoding="utf-8"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(vscode_scope_root)

            from lg.engine import run_render
            from lg.types import RunOptions

            options = RunOptions(
                tokenizer_lib="tiktoken",
                encoder="cl100k_base",
                ctx_limit=128000,
            )

            with pytest.raises(Exception) as exc_info:
                run_render("bad", options)

            # Should fail with scope not found error
            error_msg = str(exc_info.value).lower()
            assert "not found" in error_msg or "scope" in error_msg

        finally:
            os.chdir(original_cwd)
