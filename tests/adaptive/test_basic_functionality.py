"""
Basic tests for adaptive features.

Tests the basic functionality of modes, tags, and their impact on context generation.
"""

from __future__ import annotations

import pytest

from lg.engine import run_report
from .conftest import (
    adaptive_project, make_run_options, make_engine,
    create_conditional_template, render_template
)


def test_basic_modes_loading(adaptive_project):
    """Test basic mode loading from configuration."""
    root = adaptive_project

    # Test loading modes without activation
    options = make_run_options()
    engine = make_engine(root, options)

    modes_config = engine.run_ctx.adaptive_loader.get_modes_config()

    # Check that all mode sets are loaded
    assert "ai-interaction" in modes_config.mode_sets
    assert "dev-stage" in modes_config.mode_sets

    # Check specific modes
    ai_modes = modes_config.mode_sets["ai-interaction"].modes
    assert "ask" in ai_modes
    assert "agent" in ai_modes
    assert ai_modes["agent"].tags == ["agent", "tools"]

    dev_modes = modes_config.mode_sets["dev-stage"].modes
    assert "planning" in dev_modes
    assert "review" in dev_modes
    assert dev_modes["review"].options.get("vcs_mode") == "changes"


def test_basic_tags_loading(adaptive_project):
    """Test basic tag loading from configuration."""
    root = adaptive_project

    options = make_run_options()
    engine = make_engine(root, options)

    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()

    # Check tag sets
    assert "language" in tags_config.tag_sets
    assert "code-type" in tags_config.tag_sets

    language_tags = tags_config.tag_sets["language"].tags
    assert "python" in language_tags
    assert "typescript" in language_tags

    # Check global tags
    assert "agent" in tags_config.global_tags
    assert "review" in tags_config.global_tags
    assert "minimal" in tags_config.global_tags


def test_mode_activation_affects_active_tags(adaptive_project):
    """Test tag activation through modes."""
    root = adaptive_project

    # Activate a mode that adds tags
    options = make_run_options(modes={"ai-interaction": "agent"})
    engine = make_engine(root, options)

    # Check that mode tags are activated
    assert "agent" in engine.run_ctx.active_tags
    assert "tools" in engine.run_ctx.active_tags

    # Activate another mode
    options2 = make_run_options(modes={"dev-stage": "testing"})
    engine2 = make_engine(root, options2)

    assert "tests" in engine2.run_ctx.active_tags
    assert "agent" not in engine2.run_ctx.active_tags


def test_extra_tags_are_activated(adaptive_project):
    """Test activation of additional tags."""
    root = adaptive_project

    options = make_run_options(extra_tags={"minimal", "python"})
    engine = make_engine(root, options)

    assert "minimal" in engine.run_ctx.active_tags
    assert "python" in engine.run_ctx.active_tags


def test_mode_options_merging(adaptive_project):
    """Test merging of options from active modes."""
    root = adaptive_project

    # Activate a mode with options
    options = make_run_options(modes={"dev-stage": "review"})
    engine = make_engine(root, options)

    # Check that mode options were applied
    assert engine.run_ctx.mode_options.vcs_mode == "changes"

    # Activate a mode with different options
    options2 = make_run_options(modes={"ai-interaction": "agent"})
    engine2 = make_engine(root, options2)

    assert engine2.run_ctx.mode_options.allow_tools == True


def test_conditional_template_with_tags(adaptive_project):
    """Test conditional templates with tag checks."""
    root = adaptive_project

    # Create a template with a tag condition
    template_content = """# Adaptive Test

{% if tag:minimal %}
## Minimal Mode
${docs}
{% else %}
## Full Mode
${src}
${docs}
{% endif %}

{% if tag:tests %}
## Testing Section
${tests}
{% endif %}
"""

    create_conditional_template(root, "adaptive-test", template_content)

    # Test without tags
    options1 = make_run_options()
    result1 = render_template(root, "ctx:adaptive-test", options1)

    assert "Full Mode" in result1
    assert "Minimal Mode" not in result1
    assert "Testing Section" not in result1

    # Test with minimal tag
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:adaptive-test", options2)

    assert "Minimal Mode" in result2
    assert "Full Mode" not in result2

    # Test with tests tag
    options3 = make_run_options(extra_tags={"tests"})
    result3 = render_template(root, "ctx:adaptive-test", options3)

    assert "Testing Section" in result3


def test_mode_blocks_in_templates(adaptive_project):
    """Test mode blocks in templates."""
    root = adaptive_project

    template_content = """# Mode Block Test

{% mode ai-interaction:agent %}
## Agent Mode Active
${src}
{% endmode %}

## Always Visible
${docs}
"""

    create_conditional_template(root, "mode-block-test", template_content)

    # Render without activating the mode
    options1 = make_run_options()
    result1 = render_template(root, "ctx:mode-block-test", options1)

    # In the mode block, agent and tools tags should be activated
    assert "Agent Mode Active" in result1
    assert "Always Visible" in result1


def test_tagset_conditions(adaptive_project):
    """Test TAGSET conditions."""
    root = adaptive_project

    template_content = """# TagSet Test

{% if TAGSET:language:python %}
## Python Code
${src}
{% endif %}

{% if TAGSET:language:typescript %}
## TypeScript Code
${src}
{% endif %}

{% if NOT tag:javascript %}
## Not JavaScript
${docs}
{% endif %}
"""

    create_conditional_template(root, "tagset-test", template_content)

    # Test without active language tags
    options1 = make_run_options()
    result1 = render_template(root, "ctx:tagset-test", options1)

    # If no tag from the set is active, TAGSET conditions are true
    # NOT tag:javascript is true, as javascript tag is not active
    assert "Python Code" in result1
    assert "TypeScript Code" in result1
    assert "Not JavaScript" in result1

    # Activate python tag
    options2 = make_run_options(extra_tags={"python"})
    result2 = render_template(root, "ctx:tagset-test", options2)

    # Now TAGSET condition is true only for python
    # NOT tag:javascript is still true, as javascript is not active
    assert "Python Code" in result2
    assert "TypeScript Code" not in result2
    assert "Not JavaScript" in result2

    # Activate javascript tag
    options3 = make_run_options(extra_tags={"javascript"})
    result3 = render_template(root, "ctx:tagset-test", options3)

    # Now TAGSET:language:javascript is true, other TAGSET are false
    # NOT tag:javascript is false, as javascript is active
    assert "Python Code" not in result3
    assert "TypeScript Code" not in result3
    assert "Not JavaScript" not in result3


def test_complex_conditions(adaptive_project):
    """Test complex conditional expressions."""
    root = adaptive_project

    template_content = """# Complex Conditions

{% if tag:agent AND tag:tests %}
## Agent Testing Mode
${tests}
{% endif %}

{% if tag:minimal OR tag:review %}
## Minimal or Review
${docs}
{% endif %}

{% if NOT (tag:agent AND tag:tools) %}
## Not Full Agent
${src}
{% endif %}
"""

    create_conditional_template(root, "complex-test", template_content)

    # Test various tag combinations
    options1 = make_run_options(extra_tags={"agent", "tests"})
    result1 = render_template(root, "ctx:complex-test", options1)
    assert "Agent Testing Mode" in result1

    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:complex-test", options2)
    assert "Minimal or Review" in result2

    options3 = make_run_options(extra_tags={"agent"})  # without tools
    result3 = render_template(root, "ctx:complex-test", options3)
    assert "Not Full Agent" in result3


def test_mode_activation_through_cli_like_interface(adaptive_project, monkeypatch):
    """Test mode activation through CLI-like interface."""
    root = adaptive_project
    monkeypatch.chdir(root)

    # Create a simple template for testing
    create_conditional_template(root, "cli-test", """# CLI Test

{% if tag:agent %}
## Agent Active
{% endif %}

{% if tag:tests %}
## Tests Active
{% endif %}
""")

    # Test activation through modes (like in CLI --mode ai-interaction:agent)
    options = make_run_options(modes={"ai-interaction": "agent", "dev-stage": "testing"})
    result = render_template(root, "ctx:cli-test", options)

    assert "Agent Active" in result
    assert "Tests Active" in result


def test_report_includes_mode_information(adaptive_project, monkeypatch):
    """Test inclusion of mode information in report."""
    root = adaptive_project
    monkeypatch.chdir(root)

    options = make_run_options(
        modes={"ai-interaction": "agent"},
        extra_tags={"minimal"}
    )

    report = run_report("sec:src", options)

    # Check that report contains file information
    assert len(report.files) > 0

    # Check basic report structure
    assert report.total.tokensProcessed > 0
    assert report.target == "sec:src"
    assert report.scope.value == "section"


@pytest.mark.parametrize("mode_set,mode", [
    ("ai-interaction", "ask"),
    ("ai-interaction", "agent"),
    ("dev-stage", "planning"),
    ("dev-stage", "review")
])
def test_all_predefined_modes_work(adaptive_project, mode_set, mode):
    """Parametrized test of all predefined modes."""
    root = adaptive_project

    options = make_run_options(modes={mode_set: mode})
    engine = make_engine(root, options)

    # Check that mode is activated
    assert engine.run_ctx.options.modes[mode_set] == mode

    # Check that context is created without errors
    assert engine.run_ctx.root == root

    # Check basic section rendering (result may be empty for changes mode)
    result = engine.render_section("src")
    assert isinstance(result, str)  # Check that rendering completed without errors


def test_invalid_mode_raises_error(adaptive_project):
    """Test error handling when specifying an invalid mode."""
    root = adaptive_project

    # Invalid mode set
    with pytest.raises(ValueError, match="Unknown mode set 'invalid-set'"):
        options = make_run_options(modes={"invalid-set": "any-mode"})
        make_engine(root, options)

    # Invalid mode in correct set
    with pytest.raises(ValueError, match="Unknown mode 'invalid-mode' in mode set 'ai-interaction'"):
        options = make_run_options(modes={"ai-interaction": "invalid-mode"})
        make_engine(root, options)