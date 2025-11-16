"""
Tests for complex placeholder scenarios.

Checks complex usage cases:
- Mixed placeholder types in a single template
- Cascading includes across multiple scopes
- Deep nesting and complex dependencies
- Integration tests of complete processing cycle
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template,
    create_complex_federated_templates
)


def test_all_placeholder_types_in_single_template(federated_project):
    """Test all placeholder types in a single template."""
    root = federated_project

    # Create additional templates and contexts for test
    create_template(root, "intro-tpl", """# System Introduction

This is a comprehensive system overview.
""", "tpl")

    create_template(root, "summary-ctx", """# Summary Context

## Quick Overview

${overview}
""", "ctx")

    create_template(root / "apps" / "web", "web-intro-tpl", """# Web Introduction

Modern web application built with TypeScript.
""", "tpl")

    create_template(root / "libs" / "core", "core-summary-ctx", """# Core Summary

${core-lib}
""", "ctx")

    # Template using all placeholder types
    create_template(root, "comprehensive-test", """${tpl:intro-tpl}

## Project Structure

### Local Sections
${overview}
${root-config}

### Cross-Scope Sections
${@apps/web:web-src}
${@libs/core:core-lib}

### Local Templates
${tpl:intro-tpl}

### Cross-Scope Templates
${tpl@apps/web:web-intro-tpl}

### Local Contexts
${ctx:summary-ctx}

### Cross-Scope Contexts
${ctx@libs/core:core-summary-ctx}

## Conclusion

This template demonstrates all placeholder types working together.
""")

    result = render_template(root, "ctx:comprehensive-test")

    # Check content from all placeholder types

    # Local sections
    assert "Federated Project" in result

    # Cross-scope sections
    assert "export const App" in result
    assert "class Processor:" in result

    # Local templates
    assert "System Introduction" in result
    assert "comprehensive system overview" in result

    # Cross-scope templates
    assert "Web Introduction" in result
    assert "Modern web application" in result

    # Local contexts
    assert "Summary Context" in result
    assert "Quick Overview" in result

    # Cross-scope contexts
    assert "Core Summary" in result

    # Final text
    assert "all placeholder types working together" in result


def test_cascading_includes_across_multiple_scopes(federated_project):
    """Test cascading includes across multiple scopes."""
    root = federated_project

    # Create complex cascading dependency structure
    paths = create_complex_federated_templates(root)

    result = render_template(root, "ctx:full-stack")

    # Check that all cascade levels worked
    assert "Project Overview" in result  # from project-overview.tpl
    assert "Federated Project" in result  # from overview section

    assert "Web Application" in result  # from web-intro.tpl
    assert "export const App" in result  # from web-src section

    assert "Core Library API" in result  # from api-docs.tpl
    assert "def get_client():" in result  # from core-api section


def test_deeply_nested_mixed_placeholders(basic_project):
    """Test deeply nested mixed placeholders."""
    root = basic_project

    # Create complex nesting hierarchy

    # Level 4 (deepest)
    create_template(root, "level4/content", """Deep content: ${src}""", "tpl")

    # Level 3
    create_template(root, "level3/wrapper", """# Level 3

${tpl:level4/content}
""", "ctx")

    # Level 2
    create_template(root, "level2/container", """# Level 2

${ctx:level3/wrapper}

Additional docs: ${docs}
""", "tpl")

    # Level 1
    create_template(root, "level1/main", """# Level 1

${tpl:level2/container}

Tests: ${tests}
""", "ctx")

    # Main template
    create_template(root, "deeply-nested-test", """# Deeply Nested Test

${ctx:level1/main}

## Summary

This demonstrates deep nesting of mixed placeholders.
""")

    result = render_template(root, "ctx:deeply-nested-test")

    # Check that all levels worked
    assert "Level 1" in result
    assert "Level 2" in result
    assert "Level 3" in result
    assert "Deep content:" in result
    assert "def main():" in result  # from src via level4
    assert "Project Documentation" in result  # from docs via level2
    assert "def test_main():" in result  # from tests via level1
    assert "deep nesting of mixed placeholders" in result


def test_multiple_file_groups_with_mixed_placeholders(basic_project):
    """Test multiple file groups with mixed placeholders."""
    root = basic_project

    # Create additional files for testing grouping
    from .conftest import write_source_file

    write_source_file(root / "src" / "models" / "user.py", "class User: pass", "python")
    write_source_file(root / "src" / "models" / "product.py", "class Product: pass", "python")
    write_source_file(root / "src" / "api" / "handlers.py", "def handle_request(): pass", "python")

    # Create specialized sections for new files
    from .conftest import create_sections_yaml, get_basic_sections_config

    sections_config = get_basic_sections_config()
    sections_config.update({
        "models": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/models/**"]
            }
        },
        "api": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/api/**"]
            }
        }
    })
    create_sections_yaml(root, sections_config)

    # Create templates for each group
    create_template(root, "models-intro", """## Data Models

The following classes represent our data structures:
""", "tpl")

    create_template(root, "api-intro", """## API Layer

Request handling implementation:
""", "tpl")

    # Main context with multiple groups
    create_template(root, "multiple-groups-test", """# Multiple File Groups Test

## Core Implementation
${src}

${tpl:models-intro}
${models}

${tpl:api-intro}
${api}

## Documentation
${docs}

## Testing Suite
${tests}
""")

    result = render_template(root, "ctx:multiple-groups-test")

    # Check all file groups
    assert "def main():" in result  # from core src
    assert "class User: pass" in result  # from models
    assert "class Product: pass" in result  # from models
    assert "def handle_request(): pass" in result  # from api
    assert "Project Documentation" in result  # from docs
    assert "def test_main():" in result  # from tests

    # Check templates
    assert "Data Models" in result
    assert "API Layer" in result


def test_error_handling_in_complex_scenarios(federated_project):
    """Test error handling in complex scenarios."""
    root = federated_project

    # Create template with error in middle of complex structure
    create_template(root, "error-in-middle", """# Error Test

## Valid Section
${overview}

## Invalid Section (should cause error)
${@apps/web:nonexistent-section}

## This should not be reached
${@libs/core:core-lib}
""")

    # Error should interrupt processing
    with pytest.raises(TemplateProcessingError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:error-in-middle")


def test_performance_with_large_number_of_placeholders(basic_project):
    """Test performance with large number of placeholders."""
    root = basic_project

    # Create template with multiple repeats
    placeholder_content = []
    for i in range(50):  # 50 repeats of each type
        placeholder_content.extend([
            f"## Section {i}",
            "${src}",
            f"## Docs {i}",
            "${docs}",
        ])

    template_content = "# Performance Test\n\n" + "\n\n".join(placeholder_content)

    create_template(root, "performance-test", template_content)

    # Rendering should complete without errors (check key markers)
    result = render_template(root, "ctx:performance-test")

    assert "Performance Test" in result
    assert "def main():" in result
    assert "Project Documentation" in result

    # Check that content repeated correct number of times
    main_occurrences = result.count("def main():")
    assert main_occurrences == 50


def test_mixed_addressing_schemes(federated_project):
    """Test mixed addressing schemes in one document."""
    root = federated_project

    create_template(root, "mixed-addressing-test", """# Mixed Addressing Test

## Classic Addressing
${@apps/web:web-src}
${@libs/core:core-lib}

## Bracketed Addressing
${@[apps/web]:web-docs}
${@[libs/core]:core-api}

## Local References
${overview}

## Mixed in Templates
${tpl@apps/web:web-intro}
${tpl@[libs/core]:api-docs}

## Mixed in Contexts
${ctx@apps/web:web-context}
${ctx@[libs/core]:core-context}
""")

    # Create necessary templates and contexts
    create_template(root / "apps" / "web", "web-intro", """Web intro content""", "tpl")
    create_template(root / "libs" / "core", "api-docs", """API docs content""", "tpl")
    create_template(root / "apps" / "web", "web-context", """Web context content""", "ctx")
    create_template(root / "libs" / "core", "core-context", """Core context content""", "ctx")

    result = render_template(root, "ctx:mixed-addressing-test")

    # Both addressing schemes should work identically
    assert "export const App" in result  # from web-src (classic addressing)
    assert "class Processor:" in result  # from core-lib (classic addressing)
    assert "Deployment instructions" in result  # from web-docs (bracketed addressing)
    assert "def get_client():" in result  # from core-api (bracketed addressing)

    # Local references
    assert "Federated Project" in result  # from overview

    # Mixed addressing in templates and contexts
    assert "Web intro content" in result
    assert "API docs content" in result
    assert "Web context content" in result
    assert "Core context content" in result


def test_edge_case_empty_and_whitespace_handling(basic_project):
    """Test edge cases with empty content and whitespace."""
    root = basic_project

    # Create empty and nearly empty templates
    create_template(root, "empty-tpl", "", "tpl")
    create_template(root, "whitespace-only-tpl", "   \n  \n   ", "tpl")
    create_template(root, "empty-ctx", "", "ctx")

    create_template(root, "edge-cases-test", """# Edge Cases Test

Before empty template:
${tpl:empty-tpl}
After empty template.

Before whitespace template:
${tpl:whitespace-only-tpl}
After whitespace template.

Before empty context:
${ctx:empty-ctx}
After empty context.

## Normal Content
${src}
""")

    result = render_template(root, "ctx:edge-cases-test")

    # Check correct handling of edge cases
    assert "Before empty template:" in result
    assert "After empty template." in result
    assert "Before whitespace template:" in result
    assert "After whitespace template." in result
    assert "Before empty context:" in result
    assert "After empty context." in result
    assert "def main():" in result


@pytest.mark.parametrize("complexity_level", [1, 3, 5])
def test_scalable_complexity_levels(basic_project, complexity_level):
    """Parametrized test of various complexity levels."""
    root = basic_project

    # Create template with variable complexity
    content_parts = ["# Scalable Complexity Test"]

    for level in range(complexity_level):
        create_template(root, f"level-{level}", f"""## Level {level}

Content at level {level}.
""", "tpl")

        content_parts.extend([
            f"## Level {level} Section",
            f"${{tpl:level-{level}}}",
            "${src}",
            "${docs}"
        ])

    template_content = "\n\n".join(content_parts)
    create_template(root, f"complexity-{complexity_level}", template_content)

    result = render_template(root, f"ctx:complexity-{complexity_level}")

    # Check that all levels are present
    for level in range(complexity_level):
        assert f"Level {level}" in result
        assert f"Content at level {level}" in result

    # Check base content
    assert "def main():" in result
    assert "Project Documentation" in result