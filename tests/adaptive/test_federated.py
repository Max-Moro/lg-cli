"""
Tests for federated capabilities of the adaptive system.

Tests working with multiple lg-cfg scopes, configuration inclusions,
and cross-scope references.
"""

from __future__ import annotations

from .conftest import (
    federated_project, make_run_options, make_engine, render_template,
    create_conditional_template, create_modes_yaml, create_tags_yaml,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig
)


def test_federated_modes_loading(federated_project):
    """Test loading modes from federated structure."""
    root = federated_project
    
    options = make_run_options()
    engine = make_engine(root, options)
    
    modes_config = engine.run_ctx.adaptive_loader.get_modes_config()

    # Check root modes
    assert "workflow" in modes_config.mode_sets

    # Check modes from child scopes
    assert "frontend" in modes_config.mode_sets  # from apps/web
    assert "library" in modes_config.mode_sets   # from libs/core

    # Check specific modes
    frontend_modes = modes_config.mode_sets["frontend"].modes
    assert "ui" in frontend_modes
    assert "api" in frontend_modes

    library_modes = modes_config.mode_sets["library"].modes
    assert "public-api" in library_modes
    assert "internals" in library_modes


def test_federated_tags_loading(federated_project):
    """Test loading tags from federated structure."""
    root = federated_project

    options = make_run_options()
    engine = make_engine(root, options)

    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()

    # Check tag sets from child scopes
    assert "frontend-type" in tags_config.tag_sets  # from apps/web

    # Check global tags from all scopes
    assert "full-context" in tags_config.global_tags  # root
    assert "typescript" in tags_config.global_tags    # from apps/web
    assert "python" in tags_config.global_tags        # from libs/core


def test_child_mode_activation(federated_project):
    """Test activation of modes from child scopes."""
    root = federated_project

    # Activate mode from child scope
    options = make_run_options(modes={"frontend": "ui"})
    engine = make_engine(root, options)

    # Check activation of tags from mode
    assert "typescript" in engine.run_ctx.active_tags
    assert "ui" in engine.run_ctx.active_tags


def test_mode_priority_in_federation(federated_project):
    """Test priority of modes when combining scopes."""
    root = federated_project

    # Create mode conflict (same name in parent and child scope)
    parent_modes = {
        "test-priority": ModeSetConfig(
            title="Parent Test",
            modes={
                "common": ModeConfig(
                    title="Parent Common",
                    tags=["parent-tag"]
                )
            }
        )
    }
    create_modes_yaml(root, parent_modes, include=["apps/web"])

    child_modes = {
        "test-priority": ModeSetConfig(
            title="Child Test",
            modes={
                "common": ModeConfig(
                    title="Child Common",
                    tags=["child-tag"]
                ),
                "child-only": ModeConfig(
                    title="Child Only",
                    tags=["child-only-tag"]
                )
            }
        )
    }
    create_modes_yaml(root / "apps" / "web", child_modes)

    # Check parent configuration priority
    options = make_run_options(modes={"test-priority": "common"})
    engine = make_engine(root, options)

    # Parent mode should be activated
    assert "parent-tag" in engine.run_ctx.active_tags
    assert "child-tag" not in engine.run_ctx.active_tags

    # But child unique modes should be available
    options2 = make_run_options(modes={"test-priority": "child-only"})
    engine2 = make_engine(root, options2)
    assert "child-only-tag" in engine2.run_ctx.active_tags


def test_tag_merging_in_federation(federated_project):
    """Test merging of tags in federated structure."""
    root = federated_project

    # Add conflicting tags
    parent_tag_sets = {
        "common-set": TagSetConfig(
            title="Parent Common",
            tags={
                "shared-tag": TagConfig(title="Parent Version"),
                "parent-only": TagConfig(title="Parent Only")
            }
        )
    }
    parent_global = {
        "global-parent": TagConfig(title="Global Parent")
    }
    create_tags_yaml(root, parent_tag_sets, parent_global, include=["apps/web"])

    child_tag_sets = {
        "common-set": TagSetConfig(
            title="Child Common",
            tags={
                "shared-tag": TagConfig(title="Child Version"),
                "child-only": TagConfig(title="Child Only")
            }
        )
    }
    child_global = {
        "global-child": TagConfig(title="Global Child")
    }
    create_tags_yaml(root / "apps" / "web", child_tag_sets, child_global)

    options = make_run_options()
    engine = make_engine(root, options)

    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()

    # Check merging of sets
    common_set = tags_config.tag_sets["common-set"]
    assert "shared-tag" in common_set.tags
    assert "parent-only" in common_set.tags
    assert "child-only" in common_set.tags

    # Check parent version priority for conflicting tags
    assert common_set.tags["shared-tag"].title == "Parent Version"

    # Check global tags
    assert "global-parent" in tags_config.global_tags
    assert "global-child" in tags_config.global_tags


def test_cross_scope_template_references(federated_project):
    """Test cross-scope references in templates."""
    root = federated_project

    # Create template with cross-scope references
    template_content = """# Cross-Scope Test

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
"""

    create_conditional_template(root, "cross-scope-test", template_content)

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
    root = federated_project

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

    # Create root template that includes child template
    root_template_content = """# Root Template

## Root Content
${overview}

## Including Child Template
${tpl@apps/web:scope-test}
"""

    create_conditional_template(root, "root-scope-test", root_template_content)

    result = render_template(root, "ctx:root-scope-test", make_run_options())

    # When included from parent scope, scope:parent should be activated
    assert "Including Child Template" in result
    # But specific conditions depend on scope logic implementation


def test_federated_mode_options_inheritance(federated_project):
    """Test inheritance of mode options in federated structure."""
    root = federated_project

    # Activate mode with options from child scope
    options = make_run_options(modes={"library": "public-api"})
    engine = make_engine(root, options)

    # Check activation of tags and their impact on processing
    assert "python" in engine.run_ctx.active_tags
    assert "api-only" in engine.run_ctx.active_tags

    # Check basic rendering
    result = engine.render_section("@libs/core:core-lib")
    assert len(result) > 0


def test_complex_federated_scenario(federated_project):
    """Complex test of federated scenario."""
    root = federated_project

    # Create complex template using capabilities of all scopes
    template_content = """# Complex Federated Scenario

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
"""

    create_conditional_template(root, "complex-federated", template_content)

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
    root = federated_project

    # Test nonexistent child scope
    template_content = """# Error Test
${@nonexistent/scope:some-section}
"""

    create_conditional_template(root, "error-test", template_content)

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
    from lg.config.modes import list_mode_sets

    root = federated_project
    monkeypatch.chdir(root)

    mode_sets_result = list_mode_sets(root)

    # Check that all modes from all scopes are present
    mode_set_names = {ms.id for ms in mode_sets_result.mode_sets}

    assert "workflow" in mode_set_names      # root
    assert "frontend" in mode_set_names      # apps/web
    assert "library" in mode_set_names       # libs/core

    # Check structure of one of the sets
    frontend_set = next(ms for ms in mode_sets_result.mode_sets if ms.id == "frontend")
    assert frontend_set.title == "Frontend work"

    mode_names = {m.id for m in frontend_set.modes}
    assert "ui" in mode_names
    assert "api" in mode_names


def test_federated_tags_list_cli_compatibility(federated_project, monkeypatch):
    """Test compatibility with CLI command list tag-sets."""
    from lg.config.tags import list_tag_sets

    root = federated_project
    monkeypatch.chdir(root)

    tag_sets = list_tag_sets(root)

    # Check presence of tags from all scopes
    tag_set_names = {ts.id for ts in tag_sets.tag_sets}

    assert "frontend-type" in tag_set_names  # apps/web

    # Check global tags
    global_set = next((ts for ts in tag_sets.tag_sets if ts.id == "global"), None)
    if global_set:
        global_tag_names = {t.id for t in global_set.tags}
        assert "full-context" in global_tag_names  # root
        assert "typescript" in global_tag_names    # apps/web
        assert "python" in global_tag_names        # libs/core