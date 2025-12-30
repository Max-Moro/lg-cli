"""
Tests for relative path resolution in nested template inclusions.

This module tests the core requirement of the addressing system:
- Relative paths (without leading /) should resolve from CURRENT DIRECTORY of the template
- Absolute paths (with leading /) should resolve from lg-cfg root

These tests specifically target the integration between TemplateProcessor and AddressingContext,
ensuring that when processing a template in a subdirectory, relative references resolve correctly.

See also: tests/template/addressing/ for unit tests of the addressing components.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    create_template, render_template, create_sections_yaml, write
)


@pytest.fixture
def nested_templates_project(tmp_path: Path) -> Path:
    """
    Create project with nested template structure for testing
    relative path resolution in template inclusions.

    Structure:
        root/
        └── lg-cfg/
            ├── sections.yaml
            ├── agent/
            │   └── index.tpl.md          <- ROOT level agent template
            └── adapters/
                ├── _.ctx.md              <- Context that uses ${tpl:agent/index}
                └── agent/
                    └── index.tpl.md      <- ADAPTERS level agent template (EXPECTED target)
    """
    root = tmp_path

    # Create minimal sections
    sections_config = {
        "docs": {
            "extensions": [".md"],
            "filters": {"mode": "allow", "allow": ["/docs/**"]}
        }
    }
    create_sections_yaml(root, sections_config)

    # Root level agent template (should NOT be used when resolving from adapters/)
    create_template(root, "agent/index", "# ROOT AGENT INDEX\n\nThis is the ROOT level template.\n", "tpl")

    # Adapters level agent template (SHOULD be used when resolving from adapters/)
    write(root / "lg-cfg" / "adapters" / "agent" / "index.tpl.md",
          "# ADAPTERS AGENT INDEX\n\nThis is the ADAPTERS level template.\n")

    # Context in adapters/ that uses relative path
    create_template(root, "adapters/_", """# Adapters Context

## Agent Documentation

${tpl:agent/index}

## End of Context
""", "ctx")

    return root


class TestRelativePathFromSubdirectory:
    """
    Tests for relative path resolution when template is in a subdirectory.

    The key requirement:
    - When processing lg-cfg/adapters/_.ctx.md
    - A reference ${tpl:agent/index} should resolve to lg-cfg/adapters/agent/index.tpl.md
    - NOT to lg-cfg/agent/index.tpl.md
    """

    def test_relative_template_path_resolves_from_current_directory(self, nested_templates_project):
        """
        CRITICAL TEST: Relative template path should resolve from the directory
        containing the current template, not from lg-cfg root.

        Scenario:
        - Context file: lg-cfg/adapters/_.ctx.md
        - Reference: ${tpl:agent/index} (relative path, no leading /)
        - Expected: Include content from lg-cfg/adapters/agent/index.tpl.md
        - Wrong: Include content from lg-cfg/agent/index.tpl.md
        """
        root = nested_templates_project

        result = render_template(root, "ctx:adapters/_")

        # The result should contain content from ADAPTERS level template
        assert "ADAPTERS AGENT INDEX" in result, (
            f"Expected content from 'adapters/agent/index.tpl.md' but got content from root level. "
            f"Relative path 'agent/index' from 'adapters/' should resolve to 'adapters/agent/index', "
            f"not to root 'agent/index'.\n\nActual result:\n{result}"
        )

        # The result should NOT contain content from ROOT level template
        assert "ROOT AGENT INDEX" not in result, (
            f"Found content from ROOT level template, which means relative path resolution is broken. "
            f"When processing a template in lg-cfg/adapters/, path 'agent/index' should be relative "
            f"to that directory.\n\nActual result:\n{result}"
        )

    def test_absolute_template_path_resolves_from_lgcfg_root(self, nested_templates_project):
        """
        Absolute template path (with leading /) should resolve from lg-cfg root
        regardless of current template location.

        Scenario:
        - Context file: lg-cfg/adapters/_.ctx.md
        - Reference: ${tpl:/agent/index} (absolute path, with leading /)
        - Expected: Include content from lg-cfg/agent/index.tpl.md
        """
        root = nested_templates_project

        # Create context that uses absolute path
        create_template(root, "adapters/absolute-test", """# Absolute Path Test

${tpl:/agent/index}
""", "ctx")

        result = render_template(root, "ctx:adapters/absolute-test")

        # The result should contain content from ROOT level template (absolute path)
        assert "ROOT AGENT INDEX" in result, (
            f"Absolute path '/agent/index' should resolve from lg-cfg root. "
            f"Expected content from root 'agent/index.tpl.md'.\n\nActual result:\n{result}"
        )


class TestRelativeSectionPaths:
    """Tests for relative section path resolution."""

    @pytest.fixture
    def project_with_nested_sections(self, tmp_path: Path) -> Path:
        """
        Create project with sections in subdirectories.

        Structure:
            root/
            ├── lg-cfg/
            │   ├── sections.yaml (with 'docs' section)
            │   └── adapters/
            │       ├── _.sec.yaml (with 'local-docs' section)
            │       └── _.ctx.md
            └── adapters/
                └── docs/
                    └── guide.md
        """
        root = tmp_path

        # Root sections
        create_sections_yaml(root, {
            "docs": {
                "extensions": [".md"],
                "filters": {"mode": "allow", "allow": ["/docs/**"]}
            }
        })

        # Create docs at root
        write(root / "docs" / "readme.md", "# ROOT DOCS\n")

        # Sections for adapters scope (fragment)
        # Create as fragment: lg-cfg/adapters/_.sec.yaml
        write(root / "lg-cfg" / "adapters" / "_.sec.yaml",
              "local-docs:\n  extensions: ['.md']\n  filters:\n    mode: allow\n    allow:\n      - '/adapters/docs/**'\n")

        # Create adapters docs
        write(root / "adapters" / "docs" / "guide.md", "# ADAPTERS DOCS\n")

        # Context in adapters/ that references sections
        # NOTE: Section fragments in subdirectories have canonical IDs like "adapters/local-docs"
        # This is by design of the section loading system, not a bug in addressing.
        # Use the canonical ID to reference the section.
        create_template(root, "adapters/sections-test", """# Section Test

## Local Docs (using canonical section ID)

${adapters/local-docs}

## End
""", "ctx")

        return root

    def test_section_resolves_from_local_scope(self, project_with_nested_sections):
        """
        Sections defined in subdirectory fragments are accessible via their canonical ID.

        NOTE: This is not a test of relative addressing, but of section fragment naming.
        Sections in lg-cfg/adapters/_.sec.yaml get canonical IDs like "adapters/local-docs".
        """
        root = project_with_nested_sections

        result = render_template(root, "ctx:adapters/sections-test")

        # Should include content from adapters/docs/guide.md
        assert "ADAPTERS DOCS" in result, (
            f"Expected section 'adapters/local-docs' to include content from adapters/docs/. "
            f"Actual result:\n{result}"
        )


class TestNestedTemplateInclusions:
    """Tests for multi-level nested template inclusions with relative paths."""

    @pytest.fixture
    def deeply_nested_project(self, tmp_path: Path) -> Path:
        """
        Create project with deeply nested template structure.

        Structure:
            root/
            └── lg-cfg/
                ├── sections.yaml
                ├── level1/
                │   ├── entry.ctx.md       <- ${tpl:level2/middle}
                │   └── level2/
                │       ├── middle.tpl.md  <- ${tpl:level3/deep}
                │       └── level3/
                │           └── deep.tpl.md
                └── wrong/
                    └── level2/
                        └── middle.tpl.md  <- WRONG: should not be used
        """
        root = tmp_path

        create_sections_yaml(root, {
            "docs": {"extensions": [".md"], "filters": {"mode": "allow", "allow": ["/docs/**"]}}
        })

        # Correct deep hierarchy
        write(root / "lg-cfg" / "level1" / "level2" / "level3" / "deep.tpl.md",
              "# CORRECT DEEP TEMPLATE\n\nThis is at level1/level2/level3/\n")

        write(root / "lg-cfg" / "level1" / "level2" / "middle.tpl.md",
              "# MIDDLE TEMPLATE\n\n${tpl:level3/deep}\n")

        create_template(root, "level1/entry", """# Entry Point

${tpl:level2/middle}
""", "ctx")

        # Wrong path that should NOT be used
        write(root / "lg-cfg" / "wrong" / "level2" / "middle.tpl.md",
              "# WRONG MIDDLE TEMPLATE\n\nThis should never appear!\n")

        return root

    def test_deeply_nested_relative_paths(self, deeply_nested_project):
        """
        Multi-level nested template inclusions should maintain relative path context
        at each level.

        Chain: level1/entry.ctx.md -> level1/level2/middle.tpl.md -> level1/level2/level3/deep.tpl.md
        """
        root = deeply_nested_project

        result = render_template(root, "ctx:level1/entry")

        # Should include content from the correct deep template
        assert "CORRECT DEEP TEMPLATE" in result, (
            f"Expected content from 'level1/level2/level3/deep.tpl.md'. "
            f"Multi-level relative path resolution seems broken.\n\nActual result:\n{result}"
        )

        # Should include content from middle template
        assert "MIDDLE TEMPLATE" in result, (
            f"Expected content from 'level1/level2/middle.tpl.md'.\n\nActual result:\n{result}"
        )

        # Should NOT include wrong template
        assert "WRONG" not in result, (
            f"Found content from wrong path. Relative resolution is not working correctly.\n\nActual result:\n{result}"
        )


class TestParentDirectoryReferences:
    """Tests for ../ references in template paths."""

    @pytest.fixture
    def parent_ref_project(self, tmp_path: Path) -> Path:
        """
        Create project for testing ../ parent directory references.

        Structure:
            root/
            └── lg-cfg/
                ├── sections.yaml
                ├── shared/
                │   └── common.tpl.md
                └── features/
                    └── feature-a/
                        └── entry.ctx.md    <- ${tpl:../../shared/common}
        """
        root = tmp_path

        create_sections_yaml(root, {
            "docs": {"extensions": [".md"], "filters": {"mode": "allow", "allow": ["/docs/**"]}}
        })

        write(root / "lg-cfg" / "shared" / "common.tpl.md",
              "# SHARED COMMON TEMPLATE\n\nReusable content.\n")

        create_template(root, "features/feature-a/entry", """# Feature A

Using shared template via parent reference:

${tpl:../../shared/common}
""", "ctx")

        return root

    def test_parent_directory_reference_works(self, parent_ref_project):
        """
        Parent directory reference (../) should work correctly from nested templates.
        """
        root = parent_ref_project

        result = render_template(root, "ctx:features/feature-a/entry")

        assert "SHARED COMMON TEMPLATE" in result, (
            f"Expected content from 'shared/common.tpl.md' via ../../ reference. "
            f"Actual result:\n{result}"
        )
