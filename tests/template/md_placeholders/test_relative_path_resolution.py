"""
Tests for relative path resolution in md@self: placeholders.

This module tests the core requirement of the addressing system for markdown:
- Relative paths in ${md@self:path} should resolve from CURRENT DIRECTORY of the template
- Absolute paths ${md@self:/path} should resolve from lg-cfg root

These tests specifically target the integration between TemplateProcessor and AddressingContext,
ensuring that when processing a template in a subdirectory, md@self: references resolve correctly.

See also: tests/template/common_placeholders/test_relative_path_resolution.py for ${tpl:...} tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    create_template, render_template, write_markdown, create_basic_lg_cfg
)


@pytest.fixture
def nested_md_self_project(tmp_path: Path) -> Path:
    """
    Create project with nested template structure for testing
    relative path resolution in md@self: placeholders.

    Structure:
        root/
        └── lg-cfg/
            ├── sections.yaml
            ├── docs/
            │   └── guide.md              <- ROOT level docs in lg-cfg
            └── adapters/
                ├── _.ctx.md              <- Context that uses ${md@self:docs/guide}
                └── docs/
                    └── guide.md          <- ADAPTERS level docs (EXPECTED target)
    """
    root = tmp_path

    # Create basic lg-cfg
    create_basic_lg_cfg(root)

    # Root level docs in lg-cfg (should NOT be used when resolving from adapters/)
    write_markdown(root / "lg-cfg" / "docs" / "guide.md",
                   title="ROOT GUIDE",
                   content="This is the ROOT level guide in lg-cfg.")

    # Adapters level docs in lg-cfg (SHOULD be used when resolving from adapters/)
    write_markdown(root / "lg-cfg" / "adapters" / "docs" / "guide.md",
                   title="ADAPTERS GUIDE",
                   content="This is the ADAPTERS level guide.")

    # Context in adapters/ that uses relative path
    create_template(root, "adapters/_", """# Adapters Context

## Documentation

${md@self:docs/guide}

## End of Context
""", "ctx")

    return root


class TestMdSelfRelativePathFromSubdirectory:
    """
    Tests for relative path resolution when md@self: is used in a subdirectory.

    The key requirement:
    - When processing lg-cfg/adapters/_.ctx.md
    - A reference ${md@self:docs/guide} should resolve to lg-cfg/adapters/docs/guide.md
    - NOT to lg-cfg/docs/guide.md
    """

    def test_md_self_relative_path_resolves_from_current_directory(self, nested_md_self_project):
        """
        CRITICAL TEST: Relative md@self: path should resolve from the directory
        containing the current template, not from lg-cfg root.

        Scenario:
        - Context file: lg-cfg/adapters/_.ctx.md
        - Reference: ${md@self:docs/guide} (relative path, no leading /)
        - Expected: Include content from lg-cfg/adapters/docs/guide.md
        - Wrong: Include content from lg-cfg/docs/guide.md
        """
        root = nested_md_self_project

        result = render_template(root, "ctx:adapters/_")

        # The result should contain content from ADAPTERS level guide
        assert "ADAPTERS GUIDE" in result or "ADAPTERS level guide" in result, (
            f"Expected content from 'adapters/docs/guide.md' but got content from root level. "
            f"Relative path 'docs/guide' from 'adapters/' should resolve to 'adapters/docs/guide', "
            f"not to root 'docs/guide'.\n\nActual result:\n{result}"
        )

        # The result should NOT contain content from ROOT level guide
        assert "ROOT GUIDE" not in result and "ROOT level guide" not in result, (
            f"Found content from ROOT level guide, which means relative path resolution is broken. "
            f"When processing a template in lg-cfg/adapters/, path 'docs/guide' should be relative "
            f"to that directory.\n\nActual result:\n{result}"
        )

    def test_md_self_absolute_path_resolves_from_lgcfg_root(self, nested_md_self_project):
        """
        Absolute md@self: path (with leading /) should resolve from lg-cfg root
        regardless of current template location.

        Scenario:
        - Context file: lg-cfg/adapters/_.ctx.md
        - Reference: ${md@self:/docs/guide} (absolute path, with leading /)
        - Expected: Include content from lg-cfg/docs/guide.md
        """
        root = nested_md_self_project

        # Create context that uses absolute path
        create_template(root, "adapters/absolute-test", """# Absolute Path Test

${md@self:/docs/guide}
""", "ctx")

        result = render_template(root, "ctx:adapters/absolute-test")

        # The result should contain content from ROOT level guide (absolute path)
        assert "ROOT GUIDE" in result or "ROOT level guide" in result, (
            f"Absolute path '/docs/guide' should resolve from lg-cfg root. "
            f"Expected content from root 'docs/guide.md'.\n\nActual result:\n{result}"
        )


class TestMdSelfParentDirectoryReferences:
    """Tests for ../ references in md@self: paths."""

    @pytest.fixture
    def parent_ref_md_project(self, tmp_path: Path) -> Path:
        """
        Create project for testing ../ parent directory references in md@self:.

        Structure:
            root/
            └── lg-cfg/
                ├── sections.yaml
                ├── shared/
                │   └── common.md
                └── features/
                    └── feature-a/
                        └── entry.ctx.md    <- ${md@self:../../shared/common}
        """
        root = tmp_path

        create_basic_lg_cfg(root)

        write_markdown(root / "lg-cfg" / "shared" / "common.md",
                       title="SHARED COMMON DOC",
                       content="Reusable documentation content.")

        create_template(root, "features/feature-a/entry", """# Feature A

Using shared doc via parent reference:

${md@self:../../shared/common}
""", "ctx")

        return root

    def test_md_self_parent_directory_reference_works(self, parent_ref_md_project):
        """
        Parent directory reference (../) should work correctly in md@self: paths.
        """
        root = parent_ref_md_project

        result = render_template(root, "ctx:features/feature-a/entry")

        assert "SHARED COMMON DOC" in result or "Reusable documentation" in result, (
            f"Expected content from 'shared/common.md' via ../../ reference. "
            f"Actual result:\n{result}"
        )


class TestMdSelfNestedInclusions:
    """Tests for nested template inclusions with md@self: paths."""

    @pytest.fixture
    def nested_inclusion_project(self, tmp_path: Path) -> Path:
        """
        Create project with nested template that uses md@self:.

        Structure:
            root/
            └── lg-cfg/
                ├── sections.yaml
                ├── components/
                │   ├── header.tpl.md      <- ${md@self:docs/header-doc}
                │   └── docs/
                │       └── header-doc.md
                └── main.ctx.md            <- ${tpl:components/header}
        """
        root = tmp_path

        create_basic_lg_cfg(root)

        # Documentation for header component
        write_markdown(root / "lg-cfg" / "components" / "docs" / "header-doc.md",
                       title="Header Component",
                       content="Documentation for the header component.")

        # Template that uses relative md@self:
        create_template(root, "components/header", """## Header Section

${md@self:docs/header-doc}
""", "tpl")

        # Main context that includes the template
        create_template(root, "main", """# Main Application

${tpl:components/header}

## Footer
""", "ctx")

        return root

    def test_md_self_in_nested_template(self, nested_inclusion_project):
        """
        md@self: paths in nested templates should resolve relative to template location.

        Chain: main.ctx.md -> components/header.tpl.md -> components/docs/header-doc.md
        """
        root = nested_inclusion_project

        result = render_template(root, "ctx:main")

        # Should include content from header template's relative md@self reference
        assert "Header Component" in result or "header component" in result, (
            f"Expected content from 'components/docs/header-doc.md'. "
            f"md@self: in nested template should resolve relative to template location.\n\nActual result:\n{result}"
        )


class TestMdSelfWithOriginContext:
    """Tests for md@self: in contexts loaded from other origins."""

    @pytest.fixture
    def federated_md_self_project(self, tmp_path: Path) -> Path:
        """
        Create federated project where child scope uses md@self:.

        Structure:
            root/
            ├── lg-cfg/
            │   ├── sections.yaml
            │   └── main.ctx.md            <- ${ctx@apps/web:web-ctx}
            └── apps/
                └── web/
                    └── lg-cfg/
                        ├── sections.yaml
                        ├── web-ctx.ctx.md <- ${md@self:docs/internal}
                        └── docs/
                            └── internal.md
        """
        root = tmp_path

        # Root scope
        create_basic_lg_cfg(root)

        # Main context that includes child context
        create_template(root, "main", """# Main Project

## Web Application Details
${ctx@apps/web:web-ctx}

## End
""", "ctx")

        # Child scope: apps/web
        create_basic_lg_cfg(root / "apps" / "web")

        # Internal docs in child lg-cfg
        write_markdown(root / "apps" / "web" / "lg-cfg" / "docs" / "internal.md",
                       title="Web Internal Docs",
                       content="Internal documentation for web application.")

        # Child context that uses md@self: relative to child lg-cfg
        create_template(root / "apps" / "web", "web-ctx", """# Web Context

${md@self:docs/internal}
""", "ctx")

        return root

    def test_md_self_resolves_in_child_scope(self, federated_md_self_project):
        """
        md@self: in child scope context should resolve relative to child's lg-cfg.
        """
        root = federated_md_self_project

        result = render_template(root, "ctx:main")

        # Should include content from child scope's lg-cfg
        assert "Web Internal Docs" in result or "Internal documentation for web" in result, (
            f"Expected content from 'apps/web/lg-cfg/docs/internal.md'. "
            f"md@self: in child context should resolve relative to child's lg-cfg.\n\nActual result:\n{result}"
        )
