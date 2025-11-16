"""
Tests for addressed markdown placeholders.

Checks the functionality of addressed references:
- ${md@self:file} for files in lg-cfg/
- ${md@origin:file} for files from other scopes
- Federated inclusions between lg-cfg of different modules
"""

from __future__ import annotations

import pytest

from .conftest import (
    federated_md_project, md_project, create_template,
    render_template, write_markdown
)


def test_md_placeholder_with_self_origin(md_project):
    """Test ${md@self:file} for files in lg-cfg/."""
    root = md_project

    create_template(root, "self-test", """# Self Origin Test

## Internal Documentation
${md@self:internal}

## End
""")

    result = render_template(root, "ctx:self-test")

    # Check that the file from lg-cfg/ is included
    assert "Internal Documentation" in result  # from template
    assert "This is internal documentation stored in lg-cfg." in result  # from file


def test_md_placeholder_self_vs_regular(md_project):
    """Test differences between ${md@self:file} and ${md:file}."""
    root = md_project

    # Create file in both root and lg-cfg/
    from .conftest import write_markdown
    write_markdown(root / "test-file.md",
                  title="Root Version",
                  content="This is the root version of the file.")

    write_markdown(root / "lg-cfg" / "test-file.md",
                  title="LG-CFG Version",
                  content="This is the lg-cfg version of the file.")

    create_template(root, "origin-comparison", """# Origin Comparison

## Regular (from root)
${md:test-file}

## Self (from lg-cfg)
${md@self:test-file}
""")

    result = render_template(root, "ctx:origin-comparison")

    # Both files should be present (content, but not H1 headings - they are removed by strip_h1)
    assert "Root Version" not in result
    assert "LG-CFG Version" not in result
    assert "This is the root version" in result
    assert "This is the lg-cfg version" in result


def test_md_placeholder_federated_origin(federated_md_project):
    """Test ${md@origin:file} for files from other scopes."""
    root = federated_md_project

    create_template(root, "federated-test", """# Federated Test

## Main Project
${md:README}

## Web App Documentation
${md:apps/web/web-readme}

## Utility Library
${md:libs/utils/utils-readme}

## Web Deployment Guide (from web's lg-cfg)
${md@apps/web:deployment}
""")

    result = render_template(root, "ctx:federated-test")

    # Check content from root (H1 heading is removed by strip_h1)
    assert "Federated Project" not in result
    assert "Main project in a monorepo structure." in result

    # Check content from apps/web
    assert "Web Application" not in result
    assert "Frontend web application." in result
    assert "## Components" in result

    # Check content from libs/utils
    assert "Utility Library" in result
    assert "Shared utility functions." in result
    assert "## Math Utils" in result
    assert "## String Utils" in result

    # Check file from child scope lg-cfg
    assert "Web Deployment Guide" in result
    assert "How to deploy the web app." in result
    assert "npm run build" in result


def test_md_placeholder_origin_not_found_error(md_project):
    """Test error handling when origin does not exist."""
    root = md_project

    create_template(root, "bad-origin-test", """# Bad Origin Test

${md@nonexistent/module:some-file}
""")

    # Should raise an error about origin not found
    with pytest.raises(Exception):  # RuntimeError or other error
        render_template(root, "ctx:bad-origin-test")


def test_md_placeholder_file_not_found_in_origin(federated_md_project):
    """Test error handling when file is not found in the specified origin."""
    root = federated_md_project

    create_template(root, "file-not-found-test", """# File Not Found Test

${md@apps/web:nonexistent-file}
""")

    # Should raise an error about file not found in scope
    with pytest.raises(Exception):
        render_template(root, "ctx:file-not-found-test")


def test_md_placeholder_origin_without_lg_cfg(tmp_path):
    """Test error handling when origin has no lg-cfg/."""
    root = tmp_path

    # Create basic project
    from .conftest import create_basic_lg_cfg
    create_basic_lg_cfg(root)

    # Create directory without lg-cfg/
    write_markdown(root / "no-cfg" / "test.md",
                  title="Test File",
                  content="Test content")

    create_template(root, "no-cfg-test", """# No Config Test

${md@no-cfg:test}
""")

    # Should raise an error about lg-cfg not found
    with pytest.raises(Exception):  # RuntimeError: Child lg-cfg not found
        render_template(root, "ctx:no-cfg-test")


def test_md_placeholder_self_with_subdirectories(md_project):
    """Test ${md@self:path/file} with subdirectories in lg-cfg."""
    root = md_project

    # Create file in lg-cfg/ subdirectory
    write_markdown(root / "lg-cfg" / "docs" / "internal-guide.md",
                  title="Internal Guide",
                  content="Guide for internal team members.\n\n## Setup\n\nInternal setup instructions.")

    create_template(root, "self-subdir-test", """# Self Subdirectory Test

## Internal Guide
${md@self:docs/internal-guide}
""")

    result = render_template(root, "ctx:self-subdir-test")

    assert "Internal Guide" in result
    assert "Guide for internal team members." in result
    assert "## Setup" in result
    assert "Internal setup instructions." in result


@pytest.mark.parametrize("origin,filename,expected_content", [
    ("apps/web", "web-readme", "Web Application"),
    ("libs/utils", "utils-readme", "Utility Library"),
    ("apps/web", "deployment", "Web Deployment Guide")  # from lg-cfg/
])
def test_md_placeholder_federated_parametrized(federated_md_project, origin, filename, expected_content):
    """Parametrized test for federated markdown placeholders."""
    root = federated_md_project

    # Determine correct syntax depending on file type
    if filename == "deployment":
        # Files in lg-cfg use @ syntax
        placeholder = f"${{md@{origin}:{filename}}}"
    else:
        # Regular files use normal syntax with path
        placeholder = f"${{md:{origin}/{filename}}}"

    create_template(root, f"param-federated-{origin.replace('/', '-')}-{filename}", f"""# Parametrized Test

{placeholder}
""")

    result = render_template(root, f"ctx:param-federated-{origin.replace('/', '-')}-{filename}")
    assert expected_content in result


def test_md_placeholder_complex_federated_template(federated_md_project):
    """Test complex template with multiple federated inclusions."""
    root = federated_md_project

    create_template(root, "complex-federated", """# Complete Project Documentation

## Overview
${md:README}

## Applications

### Web Frontend
${md:apps/web/web-readme}

#### Deployment
${md@apps/web:deployment}

## Libraries

### Utilities
${md:libs/utils/utils-readme}

## Internal Documentation
${md@self:internal}

---
*This documentation combines content from multiple project modules.*
""")

    result = render_template(root, "ctx:complex-federated")

    # Check presence of all expected sections
    assert "Complete Project Documentation" in result
    assert "Federated Project" not in result
    assert "Web Application" not in result
    assert "Web Deployment Guide" not in result
    assert "Utility Library" not in result
    assert "Internal Documentation" in result   # self lg-cfg
    assert "*This documentation combines content" in result  # footer


def test_md_placeholder_in_nested_context_include(federated_md_project):
    """
    Test nested contexts with markdown placeholders.

    Reproduces a bug: ${ctx@apps/web:web-ctx} contains ${md:README},
    which should resolve relative to apps/web/, not the root lg-cfg/.
    """
    root = federated_md_project

    # Create local README in apps/web/
    write_markdown(root / "apps" / "web" / "README.md",
                   title="Web App README",
                   content="This is the web application README file.\n\n## Quick Start\n\n1. Install deps\n2. Run dev server")

    # Create context in apps/web/lg-cfg/ with relative markdown placeholders
    create_template(root / "apps" / "web", "web-ctx", """# Web Application Context

## Local Documentation
${md:README}

## Deployment Guide
${md@self:deployment}
""")

    # Create root context that includes child context
    create_template(root, "main-with-nested", """# Main Project

## Core
${md:README}

---

## Web Application Details
${ctx@apps/web:web-ctx}
""")

    result = render_template(root, "ctx:main-with-nested")

    # Check that root README is included in Core
    assert "Main project in a monorepo structure." in result

    # Check that Web App README is included from nested context
    assert "This is the web application README file." in result
    assert "## Quick Start" in result
    assert "1. Install deps" in result

    # Check deployment from web's lg-cfg/
    assert "How to deploy the web app." in result
    assert "npm run build" in result