"""
Tests for context placeholders.

Checks context inclusion functionality:
- ${ctx:name} - local contexts
- ${ctx@origin:name} - addressed contexts
- Nested contexts and their correct handling
- Error handling and infinite recursion prevention
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template
)


def test_simple_context_placeholder(basic_project):
    """Test simple context inclusion ${ctx:name}."""
    root = basic_project

    # Create nested context
    create_template(root, "shared-context", """# Shared Context

## Source Code Overview

${src}

## Documentation Overview

${docs}
""", "ctx")

    # Create main context that includes nested
    create_template(root, "main-with-nested-test", """# Main Context with Nested

This is the main context that includes a shared context.

${ctx:shared-context}

## Additional Testing

${tests}
""")

    result = render_template(root, "ctx:main-with-nested-test")

    # Check that nested context content is present
    assert "Shared Context" in result
    assert "Source Code Overview" in result
    assert "Documentation Overview" in result

    # Check content from sections in nested context
    assert "def main():" in result
    assert "Project Documentation" in result

    # Check content from main context
    assert "This is the main context" in result
    assert "def test_main():" in result


def test_context_placeholder_in_subdirectory(basic_project):
    """Test context inclusion from subdirectories."""
    root = basic_project

    # Create contexts in subdirectories
    create_template(root, "reports/code-report", """# Code Report

## Implementation Status

${src}

---
Generated on $(date)
""", "ctx")

    create_template(root, "reports/docs-report", """# Documentation Report

## Current Documentation

${docs}

---
Documentation is up to date.
""", "ctx")

    # Use contexts from subdirectory
    create_template(root, "subdirs-ctx-test", """# Combined Reports

## Code Analysis

${ctx:reports/code-report}

## Documentation Analysis

${ctx:reports/docs-report}
""")

    result = render_template(root, "ctx:subdirs-ctx-test")

    assert "Code Report" in result
    assert "def main():" in result
    assert "Generated on $(date)" in result

    assert "Documentation Report" in result
    assert "Project Documentation" in result
    assert "Documentation is up to date." in result


def test_context_placeholder_not_found_error(basic_project):
    """Test error when including a nonexistent context."""
    root = basic_project

    create_template(root, "bad-context-test", """# Bad Context Test

${ctx:nonexistent-context}
""")

    with pytest.raises(TemplateProcessingError, match=r"Resource not found"):
        render_template(root, "ctx:bad-context-test")


def test_addressed_context_placeholder(federated_project):
    """Test addressed context placeholders ${ctx@origin:name}."""
    root = federated_project

    # Create contexts in child scopes
    create_template(root / "apps" / "web", "web-context", """# Web Context

## Web Application Overview

${web-src}

## Web Documentation

${web-docs}

This context covers the complete web application.
""", "ctx")

    create_template(root / "libs" / "core", "core-context", """# Core Context

## Core Library Implementation

${core-lib}

## Core Public API

${core-api}

This context covers the core library functionality.
""", "ctx")

    # Main context with addressed includes
    create_template(root, "addressed-contexts-test", """# System-Wide Context

## Project Overview

${overview}

## Web Application Context

${ctx@apps/web:web-context}

## Core Library Context

${ctx@libs/core:core-context}
""")

    result = render_template(root, "ctx:addressed-contexts-test")

    # Check root content
    assert "System-Wide Context" in result
    assert "Federated Project" in result

    # Check content from web context
    assert "Web Context" in result
    assert "export const App" in result
    assert "Deployment instructions" in result
    assert "complete web application" in result

    # Check content from core context
    assert "Core Context" in result
    assert "class Processor:" in result
    assert "def get_client():" in result
    assert "core library functionality" in result


def test_nested_context_includes(basic_project):
    """Test nested context includes (ctx includes other ctx)."""
    root = basic_project

    # Create base contexts
    create_template(root, "base/code-ctx", """# Code Context

${src}
""", "ctx")

    create_template(root, "base/docs-ctx", """# Docs Context

${docs}
""", "ctx")

    # Intermediate context that combines base contexts
    create_template(root, "combined-ctx", """# Combined Context

${ctx:base/code-ctx}

${ctx:base/docs-ctx}
""", "ctx")

    # Main context that includes intermediate
    create_template(root, "nested-test", """# Nested Test

## Main Content

${ctx:combined-ctx}

## Additional Tests

${tests}
""")

    result = render_template(root, "ctx:nested-test")

    # Check all nesting levels
    assert "Code Context" in result
    assert "Docs Context" in result
    assert "def main():" in result
    assert "Project Documentation" in result
    assert "def test_main():" in result


def test_multiple_context_placeholders_same_context(basic_project):
    """Test multiple references to the same context."""
    root = basic_project

    create_template(root, "reusable-ctx", """# Reusable Context

This context can be included multiple times.

${src}
""", "ctx")

    create_template(root, "multiple-same-ctx-test", """# Multiple Same Context Test

## First Include

${ctx:reusable-ctx}

## Some Content Between

Intermediate content.

## Second Include

${ctx:reusable-ctx}
""")

    result = render_template(root, "ctx:multiple-same-ctx-test")

    # Context content should appear twice
    occurrences = result.count("Reusable Context")
    assert occurrences == 2

    occurrences = result.count("This context can be included multiple times.")
    assert occurrences == 2

    occurrences = result.count("def main():")
    assert occurrences == 2

    assert "Intermediate content." in result


def test_context_placeholder_with_templates_and_sections(basic_project):
    """Test contexts combining templates and sections."""
    root = basic_project

    # Create template for use in context
    create_template(root, "context-header", """# Generated Context Header

This context was generated automatically.
""", "tpl")

    # Create context that uses both templates and sections
    create_template(root, "mixed-ctx", """${tpl:context-header}

## Source Implementation

${src}

## Documentation

${docs}

## Summary

This context combines templates and sections effectively.
""", "ctx")

    # Use this context
    create_template(root, "mixed-usage-test", """# Mixed Usage Test

${ctx:mixed-ctx}

## Additional Testing

${tests}
""")

    result = render_template(root, "ctx:mixed-usage-test")

    assert "Generated Context Header" in result
    assert "This context was generated automatically." in result
    assert "def main():" in result
    assert "Project Documentation" in result
    assert "This context combines templates and sections effectively." in result
    assert "def test_main():" in result


def test_context_placeholder_empty_context(basic_project):
    """Test inclusion of empty context."""
    root = basic_project

    create_template(root, "empty-ctx", "", "ctx")

    create_template(root, "empty-context-test", """# Empty Context Test

Before empty context.
${ctx:empty-ctx}
After empty context.
""")

    result = render_template(root, "ctx:empty-context-test")

    assert "Before empty context." in result
    assert "After empty context." in result
    # There should be no content from empty context between them


def test_context_placeholder_whitespace_handling(basic_project):
    """Test whitespace handling around context placeholders."""
    root = basic_project

    create_template(root, "spaced-ctx", """Content with spaces.""", "ctx")

    create_template(root, "whitespace-ctx-test", """# Whitespace Test

Before context.
${ctx:spaced-ctx}
After context.

Indented:
    ${ctx:spaced-ctx}
End.
""")

    result = render_template(root, "ctx:whitespace-ctx-test")

    assert "Before context." in result
    assert "Content with spaces." in result
    assert "After context." in result
    assert "End." in result


def test_context_placeholder_mixed_local_and_addressed(federated_project):
    """Test mixed local and addressed context includes."""
    root = federated_project

    # Local context
    create_template(root, "local-ctx", """# Local Context

${overview}
""", "ctx")

    # Addressed contexts in child scopes
    create_template(root / "apps" / "web", "web-ctx", """# Web Context

${web-src}
""", "ctx")

    create_template(root / "libs" / "core", "core-ctx", """# Core Context

${core-lib}
""", "ctx")

    # Context mixing all types
    create_template(root, "mixed-contexts-test", """# Mixed Contexts Test

## Local Context

${ctx:local-ctx}

## Web Context (addressed)

${ctx@apps/web:web-ctx}

## Core Context (addressed)

${ctx@libs/core:core-ctx}
""")

    result = render_template(root, "ctx:mixed-contexts-test")

    # Local context
    assert "Local Context" in result
    assert "Federated Project" in result

    # Addressed contexts
    assert "Web Context" in result
    assert "export const App" in result

    assert "Core Context" in result
    assert "class Processor:" in result


def test_context_placeholder_case_sensitivity(basic_project):
    """Test case sensitivity in context names."""
    root = basic_project

    create_template(root, "CamelContext", """CamelContext content""", "ctx")

    # Correct case should work
    create_template(root, "case-correct-ctx-test", """${ctx:CamelContext}""")
    result = render_template(root, "ctx:case-correct-ctx-test")
    assert "CamelContext content" in result

    # Template names are case-insensitive
    create_template(root, "case-error-ctx-test", """${ctx:camelcontext}""")
    result = render_template(root, "ctx:case-error-ctx-test")
    assert "CamelContext content" in result


@pytest.mark.parametrize("context_name,content_check", [
    ("shared-context", "Shared Context"),
    ("reports/code-report", "Code Report")
])
def test_context_placeholder_parametrized(basic_project, context_name, content_check):
    """Parametrized test of various contexts."""
    root = basic_project

    # Prepare contexts
    create_template(root, "shared-context", """# Shared Context

${src}
""", "ctx")

    create_template(root, "reports/code-report", """# Code Report

${src}
""", "ctx")

    create_template(root, f"param-ctx-test-{context_name.replace('/', '-')}", f"""# Param Test

${{ctx:{context_name}}}
""")

    result = render_template(root, f"ctx:param-ctx-test-{context_name.replace('/', '-')}")
    assert content_check in result


def test_context_vs_template_placeholder_distinction(basic_project):
    """Test distinction between context and template placeholders."""
    root = basic_project

    # Create both context and template with same name
    create_template(root, "same-name", """# Template Same Name

This is a template.
""", "tpl")

    create_template(root, "same-name", """# Context Same Name

This is a context.

${src}
""", "ctx")

    # Use both types of placeholders
    create_template(root, "distinction-test", """# Distinction Test

## Template Include

${tpl:same-name}

## Context Include

${ctx:same-name}
""")

    result = render_template(root, "ctx:distinction-test")

    # Both should be present with correct content
    assert "Template Same Name" in result
    assert "This is a template." in result

    assert "Context Same Name" in result
    assert "This is a context." in result
    assert "def main():" in result  # from src section in context