"""
Tests for template placeholders.

Checks template inclusion functionality:
- ${tpl:name} - local templates
- ${tpl@origin:name} - addressed templates
- Nested includes and recursive processing
- Error handling and circular references
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template, create_nested_template_structure
)


def test_simple_template_placeholder(basic_project):
    """Test simple template inclusion ${tpl:name}."""
    root = basic_project

    # Create base template
    create_template(root, "intro", """# Project Introduction

This is a comprehensive overview of the project structure and functionality.

## Key Components

- Source code organization
- Documentation standards
- Testing framework
""", "tpl")

    # Create context that uses template
    create_template(root, "with-intro-test", """# Complete Project Context

${tpl:intro}

## Implementation Details

${src}

## Documentation

${docs}
""")

    result = render_template(root, "ctx:with-intro-test")

    # Check that template content is inserted
    assert "Project Introduction" in result
    assert "comprehensive overview" in result
    assert "Key Components" in result

    # Check that remaining content is also present
    assert "def main():" in result
    assert "Project Documentation" in result


def test_template_placeholder_in_subdirectory(basic_project):
    """Test template inclusion from subdirectories."""
    root = basic_project

    # Create template in subdirectory
    create_template(root, "common/header", """# Standard Header

Project: Test Application
Version: 1.0.0
Generated: $(date)
""", "tpl")

    create_template(root, "common/footer", """---

© 2024 Test Project. All rights reserved.
""", "tpl")

    # Use templates from subdirectory
    create_template(root, "subdirs-test", """${tpl:common/header}

## Main Content

${src}

${tpl:common/footer}
""")

    result = render_template(root, "ctx:subdirs-test")

    assert "Standard Header" in result
    assert "Project: Test Application" in result
    assert "def main():" in result
    assert "© 2024 Test Project" in result


def test_nested_template_includes(basic_project):
    """Test nested template includes (tpl includes other tpl)."""
    root = basic_project

    # Create nested template structure
    create_nested_template_structure(root)

    result = render_template(root, "ctx:basic-context")

    # Check that all nesting levels worked
    assert "Project Introduction" in result  # from intro.tpl.md
    assert "Modular architecture" in result  # from intro.tpl.md
    assert "def main():" in result  # from src section
    assert "Project Documentation" in result  # from docs section
    assert "Contact Information" in result  # from footer.tpl.md
    assert "def test_main():" in result  # from tests section


def test_template_placeholder_not_found_error(basic_project):
    """Test error when including a nonexistent template."""
    root = basic_project

    create_template(root, "bad-template-test", """# Bad Template Test

${tpl:nonexistent-template}
""")

    with pytest.raises(TemplateProcessingError, match=r"Resource not found"):
        render_template(root, "ctx:bad-template-test")


def test_addressed_template_placeholder(federated_project):
    """Test addressed template placeholders ${tpl@origin:name}."""
    root = federated_project

    # Create templates in child scopes
    create_template(root / "apps" / "web", "web-summary", """# Web Application Summary

## Source Code

${web-src}

## Configuration

The web app uses modern TypeScript and React.
""", "tpl")

    create_template(root / "libs" / "core", "core-summary", """# Core Library Summary

## Implementation

${core-lib}

## Public API

${core-api}
""", "tpl")

    # Main context with addressed includes
    create_template(root, "addressed-templates-test", """# Full System Overview

${overview}

## Web Application

${tpl@apps/web:web-summary}

## Core Library

${tpl@libs/core:core-summary}
""")

    result = render_template(root, "ctx:addressed-templates-test")

    # Check content from root section
    assert "Federated Project" in result

    # Check content from web template
    assert "Web Application Summary" in result
    assert "export const App" in result
    assert "modern TypeScript" in result

    # Check content from core template
    assert "Core Library Summary" in result
    assert "class Processor:" in result
    assert "def get_client():" in result


def test_multiple_template_placeholders_same_template(basic_project):
    """Test multiple references to the same template."""
    root = basic_project

    create_template(root, "reusable", """## Reusable Section

This section appears multiple times.
""", "tpl")

    create_template(root, "multiple-same-test", """# Multiple Same Template Test

${tpl:reusable}

## Middle Content

Some content in between.

${tpl:reusable}

## End
""")

    result = render_template(root, "ctx:multiple-same-test")

    # Template content should appear twice
    occurrences = result.count("Reusable Section")
    assert occurrences == 2

    occurrences = result.count("This section appears multiple times.")
    assert occurrences == 2

    assert "Some content in between." in result


def test_template_placeholder_with_sections_and_other_templates(basic_project):
    """Test combining templates with sections and other templates."""
    root = basic_project

    create_template(root, "code-intro", """## Source Code Analysis

The following code represents the core implementation:
""", "tpl")

    create_template(root, "code-outro", """## Code Review Notes

Please review the above implementation for:
- Performance implications
- Security considerations
- Maintainability
""", "tpl")

    create_template(root, "combined-test", """# Combined Test

${tpl:code-intro}

${src}

${tpl:code-outro}

## Additional Documentation

${docs}
""")

    result = render_template(root, "ctx:combined-test")

    # Check correct order and content
    assert "Source Code Analysis" in result
    assert "def main():" in result
    assert "Code Review Notes" in result
    assert "Project Documentation" in result

    # Check correct order of elements
    intro_pos = result.find("Source Code Analysis")
    code_pos = result.find("def main():")
    outro_pos = result.find("Code Review Notes")
    docs_pos = result.find("Project Documentation")

    assert intro_pos < code_pos < outro_pos < docs_pos


def test_deeply_nested_template_includes(basic_project):
    """Test deeply nested template includes."""
    root = basic_project

    # Create chain: level1 -> level2 -> level3 -> level4
    create_template(root, "level4", """Level 4 Content""", "tpl")

    create_template(root, "level3", """Level 3: ${tpl:level4}""", "tpl")

    create_template(root, "level2", """Level 2: ${tpl:level3}""", "tpl")

    create_template(root, "level1", """Level 1: ${tpl:level2}""", "tpl")

    create_template(root, "deep-nesting-test", """# Deep Nesting Test

${tpl:level1}
""")

    result = render_template(root, "ctx:deep-nesting-test")

    assert "Level 1: Level 2: Level 3: Level 4 Content" in result


def test_template_placeholder_with_whitespace_handling(basic_project):
    """Test whitespace handling around template placeholders."""
    root = basic_project

    create_template(root, "spaced", """Content with spaces around it.""", "tpl")

    create_template(root, "whitespace-test", """# Whitespace Test

Before template.
${tpl:spaced}
After template.

Indented:
    ${tpl:spaced}
End.
""")

    result = render_template(root, "ctx:whitespace-test")

    assert "Before template." in result
    assert "Content with spaces around it." in result
    assert "After template." in result
    assert "End." in result


def test_template_placeholder_empty_template(basic_project):
    """Test inclusion of empty template."""
    root = basic_project

    create_template(root, "empty", "", "tpl")

    create_template(root, "empty-template-test", """# Empty Template Test

Before empty.
${tpl:empty}
After empty.
""")

    result = render_template(root, "ctx:empty-template-test")

    assert "Before empty." in result
    assert "After empty." in result
    # There should be no content from empty template between them


def test_template_placeholder_mixed_local_and_addressed(federated_project):
    """Test mixed local and addressed template includes."""
    root = federated_project

    # Local template
    create_template(root, "local-intro", """# System Overview

This document covers the entire system.
""", "tpl")

    # Addressed templates in child scopes
    create_template(root / "apps" / "web", "web-details", """## Web Details

${web-src}
""", "tpl")

    create_template(root / "libs" / "core", "core-details", """## Core Details

${core-lib}
""", "tpl")

    # Context mixing all types
    create_template(root, "mixed-templates-test", """${tpl:local-intro}

${overview}

${tpl@apps/web:web-details}

${tpl@libs/core:core-details}
""")

    result = render_template(root, "ctx:mixed-templates-test")

    # Local template
    assert "System Overview" in result

    # Root section
    assert "Federated Project" in result

    # Addressed templates
    assert "Web Details" in result
    assert "Core Details" in result
    assert "export const App" in result
    assert "class Processor:" in result


@pytest.mark.parametrize("template_name,expected_content", [
    ("intro", "Project Introduction"),
    ("footer", "Contact Information")
])
def test_template_placeholder_parametrized(basic_project, template_name, expected_content):
    """Parametrized test of various templates."""
    root = basic_project

    # Create template structure beforehand
    create_nested_template_structure(root)

    create_template(root, f"param-test-{template_name}", f"""# Param Test

${{tpl:{template_name}}}
""")

    result = render_template(root, f"ctx:param-test-{template_name}")
    assert expected_content in result

def test_tpl_placeholder_in_nested_context_include(federated_project):
    """
    Test nested contexts with tpl-placeholders.

    Reproduces bug: ${ctx@apps/web:web-ctx} contains ${tpl:docs/guide},
    which should resolve relative to apps/web/lg-cfg/, not root lg-cfg/.
    """
    root = federated_project

    # Create root context that includes child context
    create_template(root, "main-with-nested", """# Main Project

## Core
${md:README}

---

## Web Application Details
${ctx@apps/web:web-ctx}
""")

    result = render_template(root, "ctx:main-with-nested")

    # Check that root README included in Core
    assert "This is a monorepo with multiple modules." in result

    # Check lg-cfg/docs/guide.tpl.md from apps/web is included
    assert "WEB GUIDE (no sections here)" in result

    # Check that Web App Deployment from apps/web is included
    assert "Deployment instructions for the web application." in result