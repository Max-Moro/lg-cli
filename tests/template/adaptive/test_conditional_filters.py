"""
Tests for conditional file filtering at different levels of FilterNode hierarchy.

Tests the when conditions in section configuration at root level
and at all nesting levels (children).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    make_run_options, render_template, write,
    TagConfig, TagSetConfig,
    create_tag_meta_section, create_integration_mode_section
)


@pytest.fixture
def hierarchical_project(tmp_path: Path) -> Path:
    """
    Creates a project with hierarchical structure for testing
    conditional filters at different levels.
    """
    root = tmp_path
    
    # Create file structure
    write(root / "pyproject.toml", "[project]\nname = 'test'\n")
    write(root / "lg" / "cli.py", "# CLI module\n")
    write(root / "lg" / "types.py", "# Types module\n")
    write(root / "lg" / "engine.py", "# Engine module\n")

    # Config sub-structure
    write(root / "lg" / "config" / "load.py", "# Config loader\n")
    write(root / "lg" / "config" / "model.py", "# Config models\n")
    write(root / "lg" / "config" / "extra.py", "# Extra config\n")

    # Adapters sub-structure
    write(root / "lg" / "adapters" / "__init__.py", "# Adapters package\n")
    write(root / "lg" / "adapters" / "registry.py", "# Registry\n")
    write(root / "lg" / "adapters" / "base.py", "# Base adapter\n")
    write(root / "lg" / "adapters" / "markdown.py", "# Markdown adapter\n")

    # Template sub-structure with plugins
    write(root / "lg" / "template" / "processor.py", "# Template processor\n")
    write(root / "lg" / "template" / "context.py", "# Template context\n")
    write(root / "lg" / "template" / "common_placeholders" / "plugin.py", "# Common placeholders\n")
    write(root / "lg" / "template" / "adaptive" / "plugin.py", "# Adaptive plugin\n")
    write(root / "lg" / "template" / "md_placeholders" / "plugin.py", "# MD placeholders\n")

    # Create tag configuration using new meta-section API
    tag_sets = {
        "template-features": TagSetConfig(
            title="Templating features",
            tags={
                "common-placeholders": TagConfig(title="Common placeholders"),
                "adaptive": TagConfig(title="Adaptive capabilities"),
                "md-placeholders": TagConfig(title="Markdown placeholders")
            }
        )
    }
    create_tag_meta_section(root, "tags", tag_sets)

    # Create integration mode-set (required for context validation)
    create_integration_mode_section(root)
    
    return root


def test_root_level_conditional_filters(hierarchical_project):
    """Test conditional filters at root level of section."""
    root = hierarchical_project

    # Configuration with conditions at root level
    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/cli.py"
      - "/lg/types.py"
    when:
      - condition: "tag:minimal"
        allow: ["/lg/engine.py"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without minimal tag - only cli.py and types.py
    result1 = render_template(root, "sec:src", make_run_options())
    assert "cli.py" in result1
    assert "types.py" in result1
    assert "engine.py" not in result1

    # With minimal tag - engine.py is added
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "cli.py" in result2
    assert "types.py" in result2
    assert "engine.py" in result2


def test_child_level_conditional_filters(hierarchical_project):
    """Test conditional filters at children level."""
    root = hierarchical_project

    # Configuration with conditions at children level
    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
          - "/adapters/"
        when:
          - condition: "tag:minimal"
            allow: ["/types.py"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without minimal tag - only config and adapters
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1 or "config" in result1
    assert "adapters/base.py" in result1 or "adapters" in result1
    assert "lg/types.py" not in result1

    # With minimal tag - types.py is added
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config" in result2
    assert "adapters" in result2
    assert "types.py" in result2


def test_deep_nested_conditional_filters(hierarchical_project):
    """Test conditional filters at deeply nested levels."""
    root = hierarchical_project

    # Configuration with conditions at deeply nested level
    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/template/"
        children:
          template:
            mode: allow
            allow:
              - "/*.py"
            when:
              - condition: "TAGSET:template-features:common-placeholders"
                allow: ["/common_placeholders/"]
              - condition: "TAGSET:template-features:adaptive"
                allow: ["/adaptive/"]
              - condition: "TAGSET:template-features:md-placeholders"
                allow: ["/md_placeholders/"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without active tags from template-features - all plugins included
    result1 = render_template(root, "sec:src", make_run_options())
    assert "processor.py" in result1
    assert "common_placeholders" in result1
    assert "adaptive" in result1
    assert "md_placeholders" in result1

    # With active common-placeholders - only it and base files
    options2 = make_run_options(extra_tags={"common-placeholders"})
    result2 = render_template(root, "sec:src", options2)
    assert "processor.py" in result2
    assert "common_placeholders" in result2
    assert "adaptive" not in result2
    assert "md_placeholders" not in result2

    # With active adaptive - only it and base files
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "processor.py" in result3
    assert "common_placeholders" not in result3
    assert "adaptive" in result3
    assert "md_placeholders" not in result3


def test_multiple_conditional_filters_same_level(hierarchical_project):
    """Test multiple conditional filters at the same level."""
    root = hierarchical_project

    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/load.py"
        when:
          - condition: "tag:minimal"
            allow: ["/adapters/"]
          - condition: "NOT tag:minimal"
            allow: ["/template/"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without minimal tag - config and template
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1
    assert "adapters" not in result1
    assert "template" in result1

    # With minimal tag - config and adapters
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config/load.py" in result2
    assert "adapters" in result2
    assert "template" not in result2


def test_conditional_filters_with_block_rules(hierarchical_project):
    """Test conditional filters with block rules."""
    root = hierarchical_project

    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
          - "/adapters/"
        when:
          - condition: "tag:minimal"
            block: ["/config/extra.py"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without minimal tag - all config files included
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1
    assert "config/model.py" in result1
    assert "config/extra.py" in result1

    # With minimal tag - extra.py blocked
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config/load.py" in result2
    assert "config/model.py" in result2
    assert "config/extra.py" not in result2


def test_conditional_filters_inheritance(hierarchical_project):
    """Test inheritance of conditional filters across levels."""
    root = hierarchical_project

    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    when:
      - condition: "tag:minimal"
        allow: ["/pyproject.toml"]
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
        when:
          - condition: "tag:minimal"
            allow: ["/adapters/"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without minimal tag - only config
    result1 = render_template(root, "sec:src", make_run_options())
    assert "pyproject.toml" not in result1
    assert "config" in result1
    assert "adapters" not in result1

    # With minimal tag - both levels apply
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "pyproject.toml" in result2
    assert "config" in result2
    assert "adapters" in result2


def test_conditional_filters_complex_conditions(hierarchical_project):
    """Test conditional filters with complex conditions."""
    root = hierarchical_project

    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
        when:
          - condition: "TAGSET:template-features:adaptive OR tag:minimal"
            allow: ["/template/"]
          - condition: "tag:minimal"
            allow: ["/adapters/"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Without tags - template is included (TAGSET without active tags = true)
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config" in result1
    assert "template" in result1
    assert "adapters" not in result1

    # With minimal - template and adapters included
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options2)
    assert "config" in result2
    assert "template" in result2
    assert "adapters" in result2

    # With adaptive from TAGSET - template included, adapters not (minimal not active)
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "config" in result3
    assert "template" in result3
    assert "adapters" not in result3


def test_conditional_filters_evaluation_error_handling(hierarchical_project):
    """Test error handling when evaluating conditions."""
    root = hierarchical_project

    # Configuration with invalid condition
    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    when:
      - condition: "tag:valid"
        allow: ["/pyproject.toml"]
      - condition: "invalid_syntax @@@ ???"
        allow: ["/lg/cli.py"]
      - condition: "tag:another_valid"
        allow: ["/lg/types.py"]
"""

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Should process without error but with warning
    # Valid conditions should be applied
    options = make_run_options(extra_tags={"valid", "another_valid"})
    result = render_template(root, "sec:src", options)

    # Valid conditions applied
    assert "pyproject.toml" in result
    assert "lg/types.py" in result

    # Invalid condition ignored (whole process doesn't fail)
    # cli.py may or may not be present depending on base rules


def test_example_from_issue(tmp_path):
    """
    Test example from task - hierarchical configuration with conditional filters.

    Verifies operation of conditions at lg/template/when level.
    """
    root = tmp_path

    # Create structure from example
    write(root / "pyproject.toml", "[project]\nname = 'lg'\n")
    write(root / "lg" / "cli.py", "# CLI\n")
    write(root / "lg" / "types.py", "# Types\n")
    write(root / "lg" / "engine.py", "# Engine\n")
    write(root / "lg" / "section_processor.py", "# Section processor\n")

    write(root / "lg" / "config" / "load.py", "# Load\n")
    write(root / "lg" / "config" / "model.py", "# Model\n")

    write(root / "lg" / "adapters" / "__init__.py", "# Init\n")
    write(root / "lg" / "adapters" / "registry.py", "# Registry\n")
    write(root / "lg" / "adapters" / "base.py", "# Base\n")
    write(root / "lg" / "adapters" / "processor.py", "# Processor\n")
    write(root / "lg" / "adapters" / "markdown.py", "# Markdown\n")

    write(root / "lg" / "template" / "processor.py", "# Template processor\n")
    write(root / "lg" / "template" / "common.py", "# Template common\n")
    write(root / "lg" / "template" / "common_placeholders" / "plugin.py", "# Common placeholders plugin\n")
    write(root / "lg" / "template" / "adaptive" / "plugin.py", "# Adaptive plugin\n")
    write(root / "lg" / "template" / "md_placeholders" / "plugin.py", "# MD placeholders plugin\n")

    # Configuration from task example
    sections_yaml = """
src:
  extends: ["ai-interaction", "tags"]
  extensions: [".py", ".toml"]
  filters:
    mode: allow
    allow:
      - "/pyproject.toml"
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/cli.py"
          - "/types.py"
          - "/engine.py"
          - "/section_processor.py"
          - "/config/"
          - "/adapters/"
          - "/template/"
        children:
          config:
            mode: allow
            allow:
              - "/load.py"
              - "/model.py"
          adapters:
            mode: allow
            allow:
              - "/__init__.py"
              - "/registry.py"
              - "/base.py"
              - "/processor.py"
              - "/markdown.py"
          template:
            mode: allow
            allow:
              - "/*.py"
            when:
              - condition: "TAGSET:template-features:common-placeholders"
                allow: ["/common_placeholders/"]
              - condition: "TAGSET:template-features:adaptive"
                allow: ["/adaptive/"]
              - condition: "TAGSET:template-features:md-placeholders"
                allow: ["/md_placeholders/"]
"""

    # Create tags using new API
    tag_sets = {
        "template-features": TagSetConfig(
            title="Templating features",
            tags={
                "common-placeholders": TagConfig(title="Common placeholders"),
                "adaptive": TagConfig(title="Adaptive capabilities"),
                "md-placeholders": TagConfig(title="Markdown placeholders")
            }
        )
    }
    create_tag_meta_section(root, "tags", tag_sets)
    create_integration_mode_section(root)

    write(root / "lg-cfg" / "sections.yaml", sections_yaml)

    # Test 1: Without active tags - all plugins included
    result1 = render_template(root, "sec:src", make_run_options())
    assert "pyproject.toml" in result1
    assert "lg/cli.py" in result1
    assert "lg/config/load.py" in result1
    assert "lg/template/processor.py" in result1
    assert "common_placeholders" in result1
    assert "adaptive" in result1
    assert "md_placeholders" in result1

    # Test 2: With active common-placeholders - only this plugin
    options2 = make_run_options(extra_tags={"common-placeholders"})
    result2 = render_template(root, "sec:src", options2)
    assert "pyproject.toml" in result2
    assert "lg/template/processor.py" in result2
    assert "common_placeholders" in result2
    assert "adaptive" not in result2
    assert "md_placeholders" not in result2

    # Test 3: With active adaptive - only this plugin
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "lg/template/processor.py" in result3
    assert "common_placeholders" not in result3
    assert "adaptive" in result3
    assert "md_placeholders" not in result3
