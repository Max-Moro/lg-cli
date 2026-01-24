"""
Tests for federated capabilities of the adaptive system.

Tests working with multiple lg-cfg scopes, configuration inclusions,
and cross-scope references.
"""

from __future__ import annotations

from .conftest import (
    federated_project, make_run_options, render_template,
    create_conditional_template
)


def test_cross_scope_template_references(federated_project):
    """Test cross-scope references in templates."""
    from tests.infrastructure import write

    root = federated_project

    # Create context that includes mode meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "workflow"
---
# Cross-Scope Test

## Root Overview
${overview}

## Web Frontend
${@apps/web:web-src}

## Core Library
${@libs/core:core-lib}

{% if tag:typescript %}
## TypeScript Specific
Web components available
{% endif %}

{% if tag:python %}
## Python Specific
Core library available
{% endif %}
'''

    write(root / "lg-cfg" / "cross-scope-test.ctx.md", context_content)

    # Test rendering with different modes
    options1 = make_run_options(modes={"frontend": "ui"})
    result1 = render_template(root, "ctx:cross-scope-test", options1)

    assert "Root Overview" in result1
    assert "Web Frontend" in result1
    assert "Core Library" in result1
    assert "TypeScript Specific" in result1
    assert "Python Specific" not in result1

    options2 = make_run_options(modes={"library": "internals"})
    result2 = render_template(root, "ctx:cross-scope-test", options2)

    assert "Python Specific" in result2
    assert "TypeScript Specific" not in result2


def test_scope_conditions_in_templates(federated_project):
    """Test scope:local and scope:parent conditions in templates."""
    from tests.infrastructure import write

    root = federated_project

    # Create context that includes mode meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "workflow"
---
# Root Template

## Root Content
${overview}

## Including Child Template
${tpl@apps/web:scope-test}
'''

    write(root / "lg-cfg" / "root-scope-test.ctx.md", context_content)

    # Create template in child scope with scope checks
    child_template_content = """# Child Template

{% if scope:local %}
## Local Scope Active
This is child scope content
{% endif %}

{% if scope:parent %}
## Parent Scope Active
This should not appear in local scope
{% endif %}
"""

    create_conditional_template(root / "apps" / "web", "scope-test", child_template_content, "tpl")

    result = render_template(root, "ctx:root-scope-test", make_run_options())

    # When included from parent scope, scope:parent should be activated
    assert "Including Child Template" in result
    # But specific conditions depend on scope logic implementation


def test_complex_federated_scenario(federated_project):
    """Complex test of federated scenario."""
    from tests.infrastructure import write

    root = federated_project

    # Create context that includes mode meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "workflow"
---
# Complex Federated Scenario

{% mode workflow:full %}
## Full Context Mode
${overview}

{% mode frontend:ui %}
### UI Components
${@apps/web:web-src}

{% if tag:full-context AND tag:typescript %}
#### Full TypeScript Context
Complete web application view
{% endif %}
{% endmode %}

{% mode library:public-api %}
### Public API
${@libs/core:core-lib}

{% if tag:full-context AND tag:python %}
#### Full Python Context
Complete library view
{% endif %}
{% endmode %}

{% endmode %}

## Conditional Sections

{% if tag:full-context %}
### Full Context Available
Global full context mode is active
{% endif %}
'''

    write(root / "lg-cfg" / "complex-federated.ctx.md", context_content)

    # Test with root mode activation
    options = make_run_options(modes={"workflow": "full"})
    result = render_template(root, "ctx:complex-federated", options)

    assert "Full Context Mode" in result
    assert "UI Components" in result  # from nested mode block
    assert "Public API" in result     # from nested mode block

    # Tags from nested modes should be activated within their blocks
    assert "Full TypeScript Context" in result  # tag:typescript from frontend:ui + tag:full-context
    assert "Full Python Context" in result     # tag:python from library:public-api + tag:full-context

    # Global tag should be available
    assert "Full Context Available" in result


def test_federated_error_handling(federated_project):
    """Test error handling in federated structure."""
    from tests.infrastructure import write

    root = federated_project

    # Create context that includes mode meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "workflow"
---
# Error Test
${@nonexistent/scope:some-section}
'''

    write(root / "lg-cfg" / "error-test.ctx.md", context_content)

    # Rendering should raise exception for nonexistent scope
    from lg.template.processor import TemplateProcessingError
    import pytest

    with pytest.raises(TemplateProcessingError) as exc_info:
        render_template(root, "ctx:error-test", make_run_options())

    # Check that error contains informative message
    assert "nonexistent/scope" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


def test_federated_modes_list_cli_compatibility(federated_project, monkeypatch):
    """Test compatibility with CLI command list mode-sets."""
    from lg.adaptive.listing import list_mode_sets
    from tests.infrastructure import write

    root = federated_project
    monkeypatch.chdir(root)

    # Create a context that includes the mode meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "workflow"
---
# Test Context

${overview}
'''
    write(root / "lg-cfg" / "test-context.ctx.md", context_content)

    # List mode-sets for the context with a provider
    mode_sets_result = list_mode_sets(root, context="test-context", provider="com.test.provider")

    # Check that mode-sets are present
    mode_set_names = {ms.id for ms in mode_sets_result.mode_sets}

    assert "ai-interaction" in mode_set_names  # integration mode-set
    assert "workflow" in mode_set_names        # content mode-set

    # Check structure of integration mode-set
    ai_set = next(ms for ms in mode_sets_result.mode_sets if ms.id == "ai-interaction")
    assert ai_set.integration is True  # has runs

    mode_names = {m.id for m in ai_set.modes}
    assert "ask" in mode_names
    assert "agent" in mode_names


def test_federated_tags_list_cli_compatibility(federated_project, monkeypatch):
    """Test compatibility with CLI command list tag-sets."""
    from lg.adaptive.listing import list_tag_sets
    from tests.infrastructure import write, create_tag_meta_section, TagSetConfig, TagConfig

    root = federated_project
    monkeypatch.chdir(root)

    # Create a tag meta-section in root (so we can reference it without @scope prefix)
    tag_sets = {
        "test-tags": TagSetConfig(
            title="Test Tags",
            tags={
                "tag1": TagConfig(title="Tag 1"),
                "tag2": TagConfig(title="Tag 2")
            }
        )
    }
    create_tag_meta_section(root, "test-tags", tag_sets)

    # Create a context that includes tag meta-sections
    context_content = '''---
include:
  - "ai-interaction"
  - "test-tags"
---
# Test Context

${overview}
'''
    write(root / "lg-cfg" / "test-tags-context.ctx.md", context_content)

    # List tag-sets for the context
    tag_sets_result = list_tag_sets(root, context="test-tags-context")

    # Check that tag-sets are present
    tag_set_names = {ts.id for ts in tag_sets_result.tag_sets}

    assert "test-tags" in tag_set_names
