"""
Tests for relative section path resolution.

These tests verify that sections can be referenced with SHORT paths
that don't duplicate the current directory prefix.

Example: from adapters/overview.ctx.md, reference ${src} instead of ${adapters/src}.
"""

from __future__ import annotations

from pathlib import Path

from .conftest import create_sections_yaml, create_template, render_template, write


class TestRelativeSectionPaths:
    """Tests for relative section path resolution."""

    def test_sections_yaml_in_subdirectory(self, tmp_path: Path):
        """
        **MOST IMPORTANT** - sections.yaml with multiple sections in subdirectory.

        Setup:
        - File: lg-cfg/adapters/sections.yaml with 4 sections
        - Sections: src, src-short, test, test-short
        - Canonical IDs: adapters/src, adapters/src-short, adapters/test, adapters/test-short

        Test:
        - From adapters/overview.ctx.md reference sections as: ${src}, ${test}
        - NOT as: ${adapters/src}, ${adapters/test}

        This is the MOST common real-world pattern and KEY benefit of relativity.
        """
        root = tmp_path

        create_sections_yaml(root, {})

        # Create adapters/sections.yaml
        write(root / "lg-cfg" / "adapters" / "sections.yaml",
              "src:\n  extensions: ['.py']\n  filters:\n    mode: allow\n    allow: ['/adapters/src/**']\n\n"
              "src-short:\n  extensions: ['.py']\n  python:\n    strip_function_bodies: true\n  filters:\n    mode: allow\n    allow: ['/adapters/src/**']\n\n"
              "test:\n  extensions: ['.py']\n  filters:\n    mode: allow\n    allow: ['/adapters/tests/**']\n\n"
              "test-short:\n  extensions: ['.py']\n  python:\n    strip_function_bodies: true\n  filters:\n    mode: allow\n    allow: ['/adapters/tests/**']\n")

        write(root / "adapters" / "src" / "main.py", "# ADAPTERS SOURCE\ndef main(): pass\n")
        write(root / "adapters" / "tests" / "test_main.py", "# ADAPTERS TESTS\ndef test_main(): pass\n")

        create_template(root, "adapters/overview", "# Overview\n${src}\n${test}\n", "ctx")

        result = render_template(root, "ctx:adapters/overview")

        assert "ADAPTERS SOURCE" in result
        assert "ADAPTERS TESTS" in result

    def test_multi_section_fragment_file(self, tmp_path: Path):
        """
        Fragment file with MULTIPLE sections.

        Setup:
        - File: lg-cfg/adapters/local.sec.yaml with 2 sections
        - Sections: src, tests
        - Canonical IDs: adapters/local/src, adapters/local/tests

        Test:
        - Reference as: ${local/src}, ${local/tests}
        - NOT as: ${adapters/local/src}, ${adapters/local/tests}
        """
        root = tmp_path

        create_sections_yaml(root, {})

        write(root / "lg-cfg" / "adapters" / "local.sec.yaml",
              "src:\n  extensions: ['.py']\n  filters:\n    mode: allow\n    allow: ['/adapters/src/**']\n\n"
              "tests:\n  extensions: ['.py']\n  filters:\n    mode: allow\n    allow: ['/adapters/tests/**']\n")

        write(root / "adapters" / "src" / "main.py", "# ADAPTERS SOURCE\ndef main(): pass\n")
        write(root / "adapters" / "tests" / "test_main.py", "# ADAPTERS TESTS\ndef test_main(): pass\n")

        create_template(root, "adapters/overview", "# Overview\n${local/src}\n${local/tests}\n", "ctx")

        result = render_template(root, "ctx:adapters/overview")

        assert "ADAPTERS SOURCE" in result
        assert "ADAPTERS TESTS" in result

    def test_single_section_fragment_file(self, tmp_path: Path):
        """
        Fragment file with SINGLE section.

        Setup:
        - File: lg-cfg/adapters/api.sec.yaml with 1 section
        - Section: src
        - Canonical ID: adapters/src (file name omitted for single section!)

        Test:
        - Reference as: ${src}
        - This is the SHORTEST possible form
        """
        root = tmp_path

        create_sections_yaml(root, {})

        write(root / "lg-cfg" / "adapters" / "api.sec.yaml",
              "src:\n  extensions: ['.py']\n  filters:\n    mode: allow\n    allow: ['/adapters/**']\n")

        write(root / "adapters" / "main.py", "# ADAPTERS SOURCE\ndef main(): pass\n")

        create_template(root, "adapters/overview", "# Overview\n${src}\n", "ctx")

        result = render_template(root, "ctx:adapters/overview")

        assert "ADAPTERS SOURCE" in result
