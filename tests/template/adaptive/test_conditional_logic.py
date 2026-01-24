"""
Tests for conditional logic in templates.

Tests the functionality of {% if %} conditional blocks, AND/OR/NOT operators,
TAGSET conditions and their combinations in adaptive templates.
"""

from __future__ import annotations

import pytest

from lg.template.processor import TemplateProcessingError
from .conftest import (
    adaptive_project, make_run_options, render_template,
    create_conditional_template, TagConfig, TagSetConfig,
    create_tag_meta_section
)


def test_basic_tag_conditions(adaptive_project):
    """Test basic tag conditions."""
    root = adaptive_project

    template_content = """# Tag Conditions Test

{% if tag:minimal %}
## Minimal section
Content for minimal mode
{% endif %}

{% if tag:nonexistent %}
## Should not appear
This should not be rendered
{% endif %}

## Always visible
This is always shown
"""

    create_conditional_template(root, "tag-conditions", template_content)

    # Test without active tags
    result1 = render_template(root, "ctx:tag-conditions", make_run_options())
    assert "Minimal section" not in result1
    assert "Should not appear" not in result1
    assert "Always visible" in result1

    # Test with active tag
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:tag-conditions", options)
    assert "Minimal section" in result2
    assert "Should not appear" not in result2
    assert "Always visible" in result2


def test_negation_conditions(adaptive_project):
    """Test NOT negation conditions."""
    root = adaptive_project

    template_content = """# Negation Test

{% if NOT tag:minimal %}
## Full mode
Complete documentation and code
{% else %}
## Minimal mode
Condensed version
{% endif %}

{% if NOT tag:nonexistent %}
## Always true
This should always appear (NOT nonexistent)
{% endif %}
"""

    create_conditional_template(root, "negation-test", template_content)

    # Without tags - NOT tag:minimal = true
    result1 = render_template(root, "ctx:negation-test", make_run_options())
    assert "Full mode" in result1
    assert "Minimal mode" not in result1
    assert "Always true" in result1

    # With minimal tag - NOT tag:minimal = false
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:negation-test", options)
    assert "Full mode" not in result2
    assert "Minimal mode" in result2
    assert "Always true" in result2


def test_and_or_conditions(adaptive_project):
    """Test AND and OR logical operators."""
    root = adaptive_project

    template_content = """# AND/OR Test

{% if tag:agent AND tag:tools %}
## Full agent mode
Both agent and tools active
{% endif %}

{% if tag:minimal OR tag:review %}
## Compact mode
Either minimal or review active
{% endif %}

{% if tag:python AND NOT tag:minimal %}
## Full Python
Complete Python documentation
{% endif %}

{% if tag:docs OR tag:architecture %}
## Documentation
Architecture or docs mode
{% endif %}
"""

    create_conditional_template(root, "and-or-test", template_content)

    # Test AND - both tags active
    options1 = make_run_options(extra_tags={"agent", "tools"})
    result1 = render_template(root, "ctx:and-or-test", options1)
    assert "Full agent mode" in result1

    # Test AND - only one tag active
    options2 = make_run_options(extra_tags={"agent"})
    result2 = render_template(root, "ctx:and-or-test", options2)
    assert "Full agent mode" not in result2

    # Test OR - one of the tags active
    options3 = make_run_options(extra_tags={"minimal"})
    result3 = render_template(root, "ctx:and-or-test", options3)
    assert "Compact mode" in result3

    options4 = make_run_options(extra_tags={"review"})
    result4 = render_template(root, "ctx:and-or-test", options4)
    assert "Compact mode" in result4

    # Test complex AND NOT combination
    options5 = make_run_options(extra_tags={"python"})
    result5 = render_template(root, "ctx:and-or-test", options5)
    assert "Full Python" in result5

    options6 = make_run_options(extra_tags={"python", "minimal"})
    result6 = render_template(root, "ctx:and-or-test", options6)
    assert "Full Python" not in result6


def test_tagset_conditions(adaptive_project):
    """Test special TAGSET conditions."""
    root = adaptive_project

    template_content = """# TAGSET Test

{% if TAGSET:language:python %}
## Python section
Python-specific content
{% endif %}

{% if TAGSET:language:typescript %}
## TypeScript section
TypeScript-specific content
{% endif %}

{% if TAGSET:code-type:tests %}
## Test code section
Test-specific content
{% endif %}

{% if TAGSET:nonexistent:any %}
## Should always show
Nonexistent tagset should be true
{% endif %}
"""

    create_conditional_template(root, "tagset-test", template_content)

    # Without active tags - all TAGSET conditions should be true
    result1 = render_template(root, "ctx:tagset-test", make_run_options())
    assert "Python section" in result1
    assert "TypeScript section" in result1
    assert "Test code section" in result1
    assert "Should always show" in result1

    # Activate python - only TAGSET:language:python should be true
    options2 = make_run_options(extra_tags={"python"})
    result2 = render_template(root, "ctx:tagset-test", options2)
    assert "Python section" in result2
    assert "TypeScript section" not in result2
    assert "Test code section" in result2  # different set, remains true

    # Activate tests from code-type set
    options3 = make_run_options(extra_tags={"tests"})
    result3 = render_template(root, "ctx:tagset-test", options3)
    assert "Python section" in result3      # language set empty, true
    assert "TypeScript section" in result3  # language set empty, true
    assert "Test code section" in result3   # tests active in code-type


def test_complex_nested_conditions(adaptive_project):
    """Test complex nested conditions."""
    root = adaptive_project

    template_content = """# Complex Conditions

{% if tag:agent %}
## Agent Mode

{% if tag:tools AND tag:review %}
### Agent with review tools
Full agent capabilities for review
{% elif tag:tools %}
### Agent with basic tools
Standard agent capabilities
{% else %}
### Basic agent
Minimal agent without tools
{% endif %}

{% if TAGSET:language:python OR TAGSET:language:typescript %}
### Language-specific agent
Agent for specific language
{% endif %}

{% endif %}

{% if NOT tag:agent AND tag:minimal %}
## Minimal non-agent mode
Simplified interface without agent
{% endif %}
"""

    create_conditional_template(root, "complex-nested", template_content)

    # Test agent with full capabilities
    options1 = make_run_options(extra_tags={"agent", "tools", "review", "python"})
    result1 = render_template(root, "ctx:complex-nested", options1)
    assert "Agent Mode" in result1
    assert "Agent with review tools" in result1
    assert "Basic agent" not in result1
    assert "Language-specific agent" in result1
    assert "Minimal non-agent mode" not in result1

    # Test agent with basic tools
    options2 = make_run_options(extra_tags={"agent", "tools"})
    result2 = render_template(root, "ctx:complex-nested", options2)
    assert "Agent Mode" in result2
    assert "Agent with basic tools" in result2
    assert "Agent with review tools" not in result2
    assert "Language-specific agent" in result2  # TAGSET without active languages = true

    # Test minimal mode without agent
    options3 = make_run_options(extra_tags={"minimal"})
    result3 = render_template(root, "ctx:complex-nested", options3)
    assert "Agent Mode" not in result3
    assert "Minimal non-agent mode" in result3


def test_parentheses_in_conditions(adaptive_project):
    """Test condition grouping with parentheses."""
    root = adaptive_project

    template_content = """# Parentheses Test

{% if (tag:python OR tag:typescript) AND tag:docs %}
## Documented language
Language with documentation
{% endif %}

{% if tag:agent AND (tag:minimal OR tag:review) %}
## Focused agent
Agent in specific mode
{% endif %}

{% if NOT (tag:agent AND tag:tools) %}
## Not full agent
Either no agent or agent without tools
{% endif %}
"""

    create_conditional_template(root, "parentheses-test", template_content)

    # Test first condition
    options1 = make_run_options(extra_tags={"python", "docs"})
    result1 = render_template(root, "ctx:parentheses-test", options1)
    assert "Documented language" in result1

    options2 = make_run_options(extra_tags={"python"})  # without docs
    result2 = render_template(root, "ctx:parentheses-test", options2)
    assert "Documented language" not in result2

    # Test second condition
    options3 = make_run_options(extra_tags={"agent", "minimal"})
    result3 = render_template(root, "ctx:parentheses-test", options3)
    assert "Focused agent" in result3

    # Test third condition (group negation)
    options4 = make_run_options(extra_tags={"agent"})  # agent without tools
    result4 = render_template(root, "ctx:parentheses-test", options4)
    assert "Not full agent" in result4

    options5 = make_run_options(extra_tags={"agent", "tools"})  # full agent
    result5 = render_template(root, "ctx:parentheses-test", options5)
    assert "Not full agent" not in result5


def test_else_and_elif_blocks(adaptive_project):
    """Test else and elif blocks."""
    root = adaptive_project

    template_content = """# Else/Elif Test

{% if tag:agent %}
## Agent active
{% elif tag:minimal %}
## Minimal mode
{% elif tag:review %}
## Review mode
{% else %}
## Default mode
{% endif %}

{% if tag:python %}
### Python detected
{% else %}
### Other language or none
{% endif %}
"""

    create_conditional_template(root, "else-elif-test", template_content)

    # Test if (first condition)
    options1 = make_run_options(extra_tags={"agent", "minimal"})  # agent takes priority
    result1 = render_template(root, "ctx:else-elif-test", options1)
    assert "Agent active" in result1
    assert "Minimal mode" not in result1
    assert "Default mode" not in result1

    # Test elif (second condition)
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:else-elif-test", options2)
    assert "Agent active" not in result2
    assert "Minimal mode" in result2
    assert "Default mode" not in result2

    # Test else (no conditions match)
    options3 = make_run_options(extra_tags={"docs"})
    result3 = render_template(root, "ctx:else-elif-test", options3)
    assert "Agent active" not in result3
    assert "Minimal mode" not in result3
    assert "Default mode" in result3

    # Test nested else
    assert "Other language or none" in result3


def test_conditions_with_mode_blocks(adaptive_project):
    """Test interaction of conditions with mode blocks."""
    root = adaptive_project

    template_content = """# Conditions with Mode Blocks

{% mode ai-interaction:agent %}
## Inside agent mode

{% if tag:tools %}
### Tools available in agent mode
{% endif %}

{% if tag:minimal %}
### Minimal agent
{% else %}
### Full agent
{% endif %}

{% endmode %}

{% if tag:agent %}
## Agent tag detected outside mode block
{% endif %}
"""

    create_conditional_template(root, "mode-conditions", template_content)

    # Test 1: without pre-activated agent tag
    result1 = render_template(root, "ctx:mode-conditions", make_run_options())

    # Inside mode block agent and tools tags are activated
    assert "Inside agent mode" in result1
    assert "Tools available in agent mode" in result1
    assert "Full agent" in result1  # tag:minimal not active
    assert "Minimal agent" not in result1

    # Outside mode block agent tag should NOT be available (mode is restored)
    assert "Agent tag detected outside mode block" not in result1

    # Test 2: with pre-activated agent tag
    result2 = render_template(root, "ctx:mode-conditions", make_run_options(extra_tags={"agent"}))

    # Inside mode block agent is still active
    assert "Inside agent mode" in result2
    assert "Tools available in agent mode" in result2
    assert "Full agent" in result2
    assert "Minimal agent" not in result2

    # Outside mode block agent tag should be available (was initially active)
    assert "Agent tag detected outside mode block" in result2


def test_custom_tagsets_in_conditions(adaptive_project):
    """Test custom tag sets in conditions."""
    root = adaptive_project

    # Add custom tag set using new meta-section API
    custom_tag_sets = {
        "feature-flags": TagSetConfig(
            title="Feature Flags",
            tags={
                "new-ui": TagConfig(title="New UI"),
                "beta-api": TagConfig(title="Beta API"),
                "experimental": TagConfig(title="Experimental")
            }
        )
    }
    create_tag_meta_section(root, "feature-flags", custom_tag_sets)

    template_content = """# Custom TagSet Test

{% if TAGSET:feature-flags:new-ui %}
## New UI enabled
Show new interface
{% endif %}

{% if TAGSET:feature-flags:beta-api %}
## Beta API enabled
Use beta endpoints
{% endif %}

{% if tag:new-ui AND tag:beta-api %}
## Both new features
Combined new features
{% endif %}
"""

    create_conditional_template(
        root, "custom-tagset", template_content,
        include_meta_sections=["ai-interaction", "dev-stage", "tags", "feature-flags"]
    )

    # Without active flags - all TAGSET conditions true
    result1 = render_template(root, "ctx:custom-tagset", make_run_options())
    assert "New UI enabled" in result1
    assert "Beta API enabled" in result1
    assert "Both new features" not in result1  # tags not active

    # Activate one flag
    options2 = make_run_options(extra_tags={"new-ui"})
    result2 = render_template(root, "ctx:custom-tagset", options2)
    assert "New UI enabled" in result2
    assert "Beta API enabled" not in result2  # other tag in set is active
    assert "Both new features" not in result2

    # Activate both flags
    options3 = make_run_options(extra_tags={"new-ui", "beta-api"})
    result3 = render_template(root, "ctx:custom-tagset", options3)
    assert "New UI enabled" in result3
    assert "Beta API enabled" in result3
    assert "Both new features" in result3


def test_invalid_condition_syntax_errors(adaptive_project):
    """Test error handling in condition syntax."""
    root = adaptive_project

    # Invalid condition syntax
    invalid_templates = [
        "{% if tag:python AND %}Invalid{% endif %}",  # incomplete AND
        "{% if OR tag:python %}Invalid{% endif %}",   # OR without left operand
        "{% if (tag:python %}Invalid{% endif %}",     # unbalanced parentheses
        "{% if tag:python) %}Invalid{% endif %}",     # extra closing parenthesis
        "{% if TAGSET:invalid %}Invalid{% endif %}",  # incomplete TAGSET
    ]

    for i, invalid_content in enumerate(invalid_templates):
        template_name = f"invalid-{i}"
        create_conditional_template(root, template_name, invalid_content)

        # Check that processing error occurs
        with pytest.raises((TemplateProcessingError, ValueError)):
            render_template(root, f"ctx:{template_name}", make_run_options())


def test_condition_evaluation_performance(adaptive_project):
    """Test performance of evaluating complex conditions."""
    root = adaptive_project

    # Create template with large number of conditions
    conditions = []
    for i in range(50):
        conditions.append(f"{{% if tag:tag{i} %}}Section {i:02d}{{% endif %}}")  # use two-digit numbers

    template_content = "# Performance Test\n\n" + "\n\n".join(conditions)
    create_conditional_template(root, "performance-test", template_content)

    # Activate some tags
    active_tags = {f"tag{i}" for i in range(0, 50, 5)}  # every 5th tag
    options = make_run_options(extra_tags=active_tags)

    # Check that rendering completes without errors
    result = render_template(root, "ctx:performance-test", options)

    # Check that activated sections are present
    for i in range(0, 50, 5):
        assert f"Section {i:02d}" in result

    # Check that non-activated sections are absent
    for i in [1, 2, 3, 4]:
        assert f"Section {i:02d}" not in result


def test_template_comments(adaptive_project):
    """Test template comments {# ... #}."""
    root = adaptive_project

    template_content = """# Template Comments Test

{# This is a comment for template developers #}
## Visible Section

Some visible content here.

{#
   Multiline comment
   that should not appear in output
   Can contain TODO, structure notes, etc.
#}

{% if tag:minimal %}
{# This comment is inside a conditional block #}
## Minimal Mode
Content for minimal mode
{% endif %}

{# Comment between sections #}

## Another Section

More visible content.

{# Final comment at the end of the document #}
"""

    create_conditional_template(root, "comments-test", template_content)

    # Test without active tags
    result1 = render_template(root, "ctx:comments-test", make_run_options())

    # Check that visible content is present
    assert "Template Comments Test" in result1
    assert "Visible Section" in result1
    assert "Some visible content here" in result1
    assert "Another Section" in result1
    assert "More visible content" in result1

    # Check that comments are removed
    assert "This is a comment for template developers" not in result1
    assert "Multiline comment" not in result1
    assert "that should not appear in output" not in result1
    assert "TODO" not in result1
    assert "Comment between sections" not in result1
    assert "Final comment" not in result1
    assert "{#" not in result1
    assert "#}" not in result1

    # Test with active tag
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:comments-test", options)

    # Check that conditional block appeared
    assert "Minimal Mode" in result2
    assert "Content for minimal mode" in result2

    # Check that comment inside conditional block is also removed
    assert "This comment is inside a conditional block" not in result2
    assert "{#" not in result2
    assert "#}" not in result2


def test_comments_with_special_characters(adaptive_project):
    """Test comments with special characters."""
    root = adaptive_project

    template_content = """# Special Characters Test

{# Comment with ${placeholder} inside #}
## Section 1

{# Comment with {% directive %} inside #}
## Section 2

{# Comment with <html> tags and "quotes" 'various' #}
## Section 3

{# Comment with symbols: @, #, $, %, ^, &, * #}
## Section 4
"""

    create_conditional_template(root, "special-chars-test", template_content)

    result = render_template(root, "ctx:special-chars-test", make_run_options())

    # Check that sections are present
    assert "Section 1" in result
    assert "Section 2" in result
    assert "Section 3" in result
    assert "Section 4" in result

    # Check that comments are removed
    assert "placeholder" not in result
    assert "directive" not in result
    assert "<html>" not in result
    assert "quotes" not in result
    # Check that comment markers are not left in unexpected places
    # (we allow '#}' in other contexts, but check that comments themselves are removed)
    assert "Comment with ${" not in result
    assert "Comment with {%" not in result
    assert "Comment with <html>" not in result
    assert "Comment with symbols" not in result


def test_adjacent_comments_and_content(adaptive_project):
    """Test comments adjacent to content without spacing."""
    root = adaptive_project

    template_content = """{# Comment at start without newline #}# Title
{# Comment after heading #}
Content line 1
{# Inline comment #}Content line 2
{# Comment before end #}"""

    create_conditional_template(root, "adjacent-test", template_content)

    result = render_template(root, "ctx:adjacent-test", make_run_options())

    # Check correct joining of content
    assert "# Title" in result
    assert "Content line 1" in result
    assert "Content line 2" in result

    # Check that comments are removed
    assert "Comment at start" not in result
    assert "Comment after heading" not in result
    assert "Inline comment" not in result
    assert "Comment before end" not in result
    assert "{#" not in result
    assert "#}" not in result