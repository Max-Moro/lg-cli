"""
Basic tests for adaptive features.

Tests the basic functionality of modes, tags, and their impact on context generation.
"""

from __future__ import annotations

import pytest

from lg.engine import run_report
from lg.adaptive.errors import UnknownModeSetError, InvalidModeReferenceError
from .conftest import (
    adaptive_project, make_run_options, make_engine,
    create_conditional_template, render_template
)


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

    # Invalid mode set - validation happens at render time, not engine creation
    with pytest.raises(UnknownModeSetError, match="Unknown mode set 'invalid-set'"):
        options = make_run_options(modes={"invalid-set": "any-mode"})
        render_template(root, "sec:src", options)

    # Invalid mode in correct set
    with pytest.raises(InvalidModeReferenceError, match="invalid-mode"):
        options = make_run_options(modes={"ai-interaction": "invalid-mode"})
        render_template(root, "sec:src", options)