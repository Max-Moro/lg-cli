"""
Tests for edge cases of adaptive features.

Tests system behavior in non-standard situations, error handling,
performance, and compatibility.
"""

from __future__ import annotations

import pytest

from .conftest import (
    adaptive_project, make_run_options, make_engine, render_template,
    create_conditional_template, create_modes_yaml, create_tags_yaml,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig
)


def test_empty_configuration_defaults(tmp_path):
    """Test behavior when adaptive features configuration is absent."""
    from tests.infrastructure.file_utils import write

    root = tmp_path

    # Create project without modes.yaml and tags.yaml
    write(root / "lg-cfg" / "sections.yaml", """
test-section:
  extensions: [".txt"]
  filters:
    mode: allow
    allow:
      - "/**"
""")

    write(root / "test.txt", "Hello, world!")

    # Should use default values
    options = make_run_options()
    engine = make_engine(root, options)

    modes_config = engine.run_ctx.adaptive_loader.get_modes_config()
    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()

    # Check presence of default modes
    assert "ai-interaction" in modes_config.mode_sets
    assert "dev-stage" in modes_config.mode_sets

    # Check basic functionality
    result = engine.render_section("test-section")
    assert "Hello, world!" in result


def test_circular_includes_prevention(tmp_path):
    """Test prevention of circular includes in federated structure."""
    from tests.infrastructure.file_utils import write

    root = tmp_path

    # Create circular includes: root -> child -> root
    create_modes_yaml(root, {}, include=["child"])
    create_modes_yaml(root / "child", {}, include=["../"])  # circular reference

    # Create minimal sections
    write(root / "lg-cfg" / "sections.yaml", """
root-sec:
  extensions: [".txt"]
  filters:
    mode: allow
    allow: ["/root.txt"]
""")

    write(root / "child" / "lg-cfg" / "sections.yaml", """
child-sec:
  extensions: [".txt"]
  filters:
    mode: allow
    allow: ["/child.txt"]
""")

    write(root / "root.txt", "root")
    write(root / "child.txt", "child")

    # System should handle this correctly (without infinite recursion)
    options = make_run_options()
    engine = make_engine(root, options)

    # Should work without hanging
    assert engine.run_ctx.adaptive_loader is not None


def test_extremely_long_tag_names(adaptive_project):
    """Test very long tag and mode names."""
    root = adaptive_project

    # Create mode with very long name
    long_name = "very-long-mode-name-that-exceeds-normal-expectations" * 5
    long_modes = {
        "long-test": ModeSetConfig(
            title="Long Test",
            modes={
                long_name: ModeConfig(
                    title="Long Mode",
                    tags=[f"long-tag-{i}" for i in range(50)]
                )
            }
        )
    }
    create_modes_yaml(root, long_modes, append=True)

    # Create template with long names
    long_tags = [f"long-tag-{i}" for i in range(20)]
    conditions = [f"{{% if tag:{tag} %}}{tag} active{{% endif %}}" for tag in long_tags[:5]]
    template_content = f"# Long Names Test\n\n" + "\n".join(conditions)

    create_conditional_template(root, "long-names-test", template_content)

    # Activate mode with long name
    options = make_run_options(modes={"long-test": long_name})
    result = render_template(root, "ctx:long-names-test", options)

    # Check that long tags are activated
    for i in range(5):
        assert f"long-tag-{i} active" in result


def test_unicode_in_configurations(adaptive_project):
    """Test Unicode support in configurations."""
    root = adaptive_project

    # Create modes with Unicode names and descriptions
    unicode_modes = {
        "international": ModeSetConfig(
            title="International mode",
            modes={
                "russian": ModeConfig(
                    title="Russian language",
                    description="Support for Russian language",
                    tags=["russian", "cyrillic"]
                ),
                "chinese": ModeConfig(
                    title="Chinese support",
                    tags=["chinese", "hanzi"]
                )
            }
        )
    }
    create_modes_yaml(root, unicode_modes, append=True)

    unicode_tags = {
        "languages": TagSetConfig(
            title="World languages",
            tags={
                "russian": TagConfig(title="Russian"),
                "chinese": TagConfig(title="Chinese"),
                "arabic": TagConfig(title="Arabic")
            }
        )
    }
    create_tags_yaml(root, unicode_tags, append=True)

    template_content = """# Unicode Test

{% if tag:russian %}
## Russian content
This is Russian text
{% endif %}

{% if tag:chinese %}
## Chinese content
This is Chinese text
{% endif %}
"""

    create_conditional_template(root, "unicode-test", template_content)

    # Activate Unicode mode
    options = make_run_options(modes={"international": "russian"})
    result = render_template(root, "ctx:unicode-test", options)

    assert "Russian content" in result
    assert "This is Chinese text" not in result  # chinese tag not active


def test_massive_number_of_tags(adaptive_project):
    """Test performance with large number of tags."""
    root = adaptive_project

    # Create large number of tags
    massive_tag_sets = {}
    for i in range(10):  # 10 sets
        tags = {}
        for j in range(100):  # 100 tags in each
            tags[f"tag-{i}-{j}"] = TagConfig(title=f"Tag {i}-{j}")

        massive_tag_sets[f"set-{i}"] = TagSetConfig(
            title=f"Set {i}",
            tags=tags
        )

    create_tags_yaml(root, massive_tag_sets, append=True)

    # Create template with multiple tag conditions (check specific tag activity)
    conditions = []
    for i in range(5):
        for j in range(10):
            conditions.append(f"{{% if tag:tag-{i}-{j} %}}Tag {i}-{j} active{{% endif %}}")

    template_content = "# Massive Tags Test\n\n" + "\n".join(conditions)
    create_conditional_template(root, "massive-tags-test", template_content)

    # Activate some tags
    active_tags = {f"tag-0-{j}" for j in range(5)}  # tags from first set
    options = make_run_options(extra_tags=active_tags)

    # Check that rendering completes in reasonable time
    result = render_template(root, "ctx:massive-tags-test", options)

    # Check result
    for j in range(5):
        assert f"Tag 0-{j} active" in result

    # Tags from other sets should not be activated
    assert "Tag 1-0 active" not in result


def test_deeply_nested_conditions(adaptive_project):
    """Test deeply nested conditional blocks."""
    root = adaptive_project

    # Create deeply nested condition structure
    template_content = """# Deeply Nested Test

{% if tag:level1 %}
## Level 1
{% if tag:level2 %}
### Level 2
{% if tag:level3 %}
#### Level 3
{% if tag:level4 %}
##### Level 4
{% if tag:level5 %}
###### Level 5
Deep nesting works!
{% endif %}
{% endif %}
{% endif %}
{% endif %}
{% endif %}
"""

    create_conditional_template(root, "deep-nesting-test", template_content)

    # Test with partial activation
    options1 = make_run_options(extra_tags={"level1", "level2"})
    result1 = render_template(root, "ctx:deep-nesting-test", options1)
    assert "Level 1" in result1
    assert "Level 2" in result1
    assert "Level 3" not in result1

    # Test with full activation
    options2 = make_run_options(extra_tags={f"level{i}" for i in range(1, 6)})
    result2 = render_template(root, "ctx:deep-nesting-test", options2)
    assert "Deep nesting works!" in result2


def test_mode_block_error_recovery(adaptive_project):
    """Test error recovery in mode blocks."""
    root = adaptive_project

    # Create template with potentially problematic mode blocks
    template_content = """# Mode Block Recovery Test

{% mode ai-interaction:agent %}
## Inside agent mode
Content 1
{% endmode %}

Normal content between blocks

{% mode invalid-set:invalid-mode %}
## This should cause error handling
Content 2
{% endmode %}

More normal content

{% mode dev-stage:testing %}
## This should still work
Content 3
{% endmode %}
"""

    create_conditional_template(root, "mode-error-test", template_content)

    # Check error handling
    with pytest.raises(Exception):  # Expect error due to invalid-set
        render_template(root, "ctx:mode-error-test", make_run_options())


def test_tagset_with_empty_sets(adaptive_project):
    """Test TAGSET conditions with empty tag sets."""
    root = adaptive_project

    # Create tag set with empty content
    empty_tag_sets = {
        "empty-set": TagSetConfig(
            title="Empty Set",
            tags={}  # empty tag set
        )
    }
    create_tags_yaml(root, empty_tag_sets, append=True)

    template_content = """# Empty TagSet Test

{% if TAGSET:empty-set:any %}
## Empty set condition
Should always be true for empty set
{% endif %}

{% if TAGSET:nonexistent-set:any %}
## Nonexistent set condition
Should always be true for nonexistent set
{% endif %}
"""

    create_conditional_template(root, "empty-tagset-test", template_content)

    result = render_template(root, "ctx:empty-tagset-test", make_run_options())

    # Empty and nonexistent sets should evaluate to true
    assert "Empty set condition" in result
    assert "Nonexistent set condition" in result


def test_memory_usage_with_large_templates(adaptive_project):
    """Test memory usage with large templates."""
    root = adaptive_project

    # Create very large template
    large_sections = []
    for i in range(200):
        large_sections.append(f"""
## Section {i}

{{% if tag:section-{i} %}}
Section {i} is active with lots of content here.
This section contains multiple paragraphs and detailed information
that would normally be quite lengthy in a real scenario.
{{% endif %}}
""")

    template_content = "# Large Template Test\n" + "\n".join(large_sections)
    create_conditional_template(root, "large-template-test", template_content)

    # Activate some sections
    active_tags = {f"section-{i}" for i in range(0, 200, 10)}  # every 10th section
    options = make_run_options(extra_tags=active_tags)

    # Check that rendering completes without memory issues
    result = render_template(root, "ctx:large-template-test", options)

    # Check that active sections are present
    for i in range(0, 200, 10):
        assert f"Section {i} is active" in result


def test_special_characters_in_tag_names(adaptive_project):
    """Test special characters in tag names."""
    root = adaptive_project

    # Create tags with special characters (only allowed in lexer)
    special_global_tags = {
        "tag_with_underscore": TagConfig(title="Underscore Tag"),
        "tag123": TagConfig(title="Number Tag"),
        "CamelCaseTag": TagConfig(title="Camel Case Tag"),
        "UPPER_TAG": TagConfig(title="Upper Case Tag")
    }
    create_tags_yaml(root, global_tags=special_global_tags, append=True)

    template_content = """# Special Characters Test

{% if tag:tag_with_underscore %}
## Underscore tag active
{% endif %}

{% if tag:tag123 %}
## Number tag active
{% endif %}

{% if tag:CamelCaseTag %}
## Camel case tag active
{% endif %}

{% if tag:UPPER_TAG %}
## Upper case tag active
{% endif %}
"""

    create_conditional_template(root, "special-chars-test", template_content)

    # Activate all special tags
    options = make_run_options(extra_tags={
        "tag_with_underscore", "tag123", "CamelCaseTag", "UPPER_TAG"
    })
    result = render_template(root, "ctx:special-chars-test", options)

    assert "Underscore tag active" in result
    assert "Number tag active" in result
    assert "Camel case tag active" in result
    assert "Upper case tag active" in result


def test_configuration_reload_behavior(adaptive_project):
    """Test behavior when configuration changes during execution."""
    root = adaptive_project

    # Create initial engine
    engine1 = make_engine(root, make_run_options())
    initial_modes = set(engine1.run_ctx.adaptive_loader.get_modes_config().mode_sets.keys())

    # Add new configuration
    new_modes = {
        "runtime-added": ModeSetConfig(
            title="Runtime Added",
            modes={
                "new-mode": ModeConfig(title="New Mode", tags=["new-tag"])
            }
        )
    }
    create_modes_yaml(root, new_modes, append=True)

    # Create new engine (should see new configuration)
    engine2 = make_engine(root, make_run_options())
    updated_modes = set(engine2.run_ctx.adaptive_loader.get_modes_config().mode_sets.keys())

    # New engine should see updated configuration
    assert "runtime-added" in updated_modes
    assert "runtime-added" not in initial_modes


def test_backwards_compatibility_warnings(adaptive_project):
    """Test warnings for compatibility with deprecated formats."""
    # This test can be extended in the future when new API versions are added
    root = adaptive_project

    # For now just check that current format works
    options = make_run_options()
    engine = make_engine(root, options)

    # Check that system works with current configurations
    assert engine.run_ctx.adaptive_loader is not None
    assert len(engine.run_ctx.adaptive_loader.get_modes_config().mode_sets) > 0


@pytest.mark.slow
def test_performance_regression_detection(adaptive_project):
    """Test for detecting performance regressions."""
    import time

    root = adaptive_project

    # Create load test
    heavy_template = """# Performance Test

{% for i in range(100) %}
{% if tag:perf-{{ i }} %}
## Section {{ i }}
Content for section {{ i }}
{% endif %}
{% endfor %}
"""

    # Note: This is pseudo-code since for loops are not supported in current implementation
    # Replace with manual condition creation
    conditions = []
    for i in range(100):
        conditions.append(f"{{% if tag:perf-{i} %}}## Section {i}\nContent for section {i}{{% endif %}}")

    template_content = "# Performance Test\n\n" + "\n\n".join(conditions)
    create_conditional_template(root, "performance-regression-test", template_content)

    # Measure rendering time
    start_time = time.time()

    options = make_run_options(extra_tags={f"perf-{i}" for i in range(50)})
    result = render_template(root, "ctx:performance-regression-test", options)

    end_time = time.time()

    # Check that rendering completed in reasonable time (< 5 seconds)
    assert (end_time - start_time) < 5.0, f"Rendering took too long: {end_time - start_time} seconds"

    # Check correctness of result
    for i in range(50):
        assert f"Section {i}" in result