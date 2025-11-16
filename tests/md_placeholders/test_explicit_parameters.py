"""
Tests for explicit parameters in markdown placeholders.

Checks the functionality of automatic settings override:
- ${md:file, level:4, strip_h1:false}
- Priority of explicit parameters over contextual analysis
- Different parameter combinations
- Handling of incorrect parameters
"""

from __future__ import annotations

import pytest

from .conftest import md_project, create_template, render_template


def test_explicit_level_parameter(md_project):
    """Test explicit level parameter to override max_heading_level."""
    root = md_project

    create_template(root, "explicit-level-test", """# Main Document

## Default Context (should be level 3)
${md:docs/api}

## Explicit Level 5
${md:docs/api, level:5}

## Explicit Level 2
${md:docs/guide, level:2}
""")

    result = render_template(root, "ctx:explicit-level-test")

    # First inclusion: contextual analysis (under H2 → max_heading_level=3, strip_h1=true)
    # H1 headings are removed, only H2 headings remain as H3

    # Check that H1 headings are removed (contextual analysis)
    assert "### API Reference" not in result  # H1 removed
    assert "### User Guide" not in result    # H1 removed

    # Check that H2 headings are present at correct levels
    assert "### Authentication" in result    # from api.md, became H3 (contextual)
    assert "##### Authentication" in result   # from api.md, became H5 (explicit level:5)
    assert "## Installation" in result      # from guide.md, became H2 (explicit level:2)
    assert "## Usage" in result              # from guide.md, became H2 (explicit level:2)


def test_explicit_strip_h1_parameter(md_project):
    """Test explicit strip_h1 parameter."""
    root = md_project

    create_template(root, "explicit-strip-test", """# Documentation

## Section with H1 preserved
${md:docs/api, strip_h1:false}

## Section with H1 removed
${md:docs/guide, strip_h1:true}
""")

    result = render_template(root, "ctx:explicit-strip-test")

    # strip_h1:false - H1 should be preserved and become H3 (under H2)
    assert "### API Reference" in result

    # strip_h1:true - H1 should be removed, other headings shifted
    lines = result.split('\n')

    # Should not have H3 "User Guide" (removed)
    guide_h3_lines = [line for line in lines if line.strip() == "### User Guide"]
    assert len(guide_h3_lines) == 0

    # But H2 headings from guide should be present as H3
    assert "### Installation" in result  # was H2, became H3
    assert "### Usage" in result         # was H2, became H3


def test_explicit_parameters_combination(md_project):
    """Test combination of explicit parameters level and strip_h1."""
    root = md_project

    create_template(root, "combo-params-test", """# Test Document

${md:docs/api, level:4, strip_h1:false}

${md:docs/guide, level:6, strip_h1:true}
""")

    result = render_template(root, "ctx:combo-params-test")

    # api.md: level:4, strip_h1:false
    assert "#### API Reference" in result    # H1→H4, preserved
    assert "##### Authentication" in result  # H2→H5

    # guide.md: level:6, strip_h1:true
    # H1 removed, H2 become H6
    assert "###### Installation" in result   # was H2, became H6
    assert "###### Usage" in result          # was H2, became H6

    # H1 "User Guide" should not exist
    lines = result.split('\n')
    guide_h6_lines = [line for line in lines if line.strip().startswith("###### ") and "User Guide" in line]
    assert len(guide_h6_lines) == 0


def test_explicit_parameters_override_contextual_analysis(md_project):
    """Test that explicit parameters override contextual analysis."""
    root = md_project

    create_template(root, "override-contextual-test", """# Main

## Deep Section

### Very Deep

#### Super Deep

##### Extremely Deep

###### Maximum Depth Context

${md:docs/api, level:2, strip_h1:false}
""")

    result = render_template(root, "ctx:override-contextual-test")

    # Despite deep nesting (H6), explicit parameters should work
    assert "## API Reference" in result     # level:2, strip_h1:false
    assert "### Authentication" in result   # was H2, became H3


def test_explicit_level_parameter_edge_cases(md_project):
    """Test edge cases for level parameter."""
    root = md_project

    create_template(root, "level-edges-test", """# Edge Cases

## Level 1 (minimum)
${md:docs/api, level:1}

## Level 6 (maximum valid)
${md:docs/guide, level:6}
""")

    result = render_template(root, "ctx:level-edges-test")

    # level:1 - minimum level, but H1 is removed by contextual analysis
    assert "# API Reference" not in result  # H1 removed by contextual analysis
    assert "# Authentication" in result      # H2→H1 (level:1, but H1 removed)

    # level:6 - maximum level, but H1 is removed by contextual analysis
    assert "###### User Guide" not in result  # H1 removed by contextual analysis
    assert "###### Installation" in result    # H2→H6 (level:6, but H1 removed)
    assert "###### Usage" in result            # H2→H6 (level:6, but H1 removed)

    # H2 cannot become H7 (invalid), should remain H6 or be handled differently
    lines = result.split('\n')
    h7_lines = [line for line in lines if line.startswith('#######')]
    assert len(h7_lines) == 0, "Found invalid H7+ headings"


def test_invalid_level_parameter_error(md_project):
    """Test handling of incorrect level parameter values."""
    root = md_project

    # Test different incorrect values
    test_cases = [
        "${md:docs/api, level:0}",     # below minimum
        "${md:docs/api, level:7}",     # above maximum
        "${md:docs/api, level:abc}",   # not a number
        "${md:docs/api, level:}",      # empty value
    ]

    for i, invalid_placeholder in enumerate(test_cases):
        create_template(root, f"invalid-level-{i}", f"""# Invalid Level Test

{invalid_placeholder}
""")

        # Should raise validation error
        with pytest.raises(Exception):  # ValueError or other validation error
            render_template(root, f"ctx:invalid-level-{i}")


def test_invalid_strip_h1_parameter_error(md_project):
    """Test handling of incorrect strip_h1 parameter values."""
    root = md_project

    test_cases = [
        "${md:docs/api, strip_h1:invalid}",  # invalid value
        "${md:docs/api, strip_h1:}",          # empty value
    ]

    for i, invalid_placeholder in enumerate(test_cases):
        create_template(root, f"invalid-strip-{i}", f"""# Invalid Strip Test

{invalid_placeholder}
""")

        with pytest.raises(Exception):  # ValueError or other validation error
            render_template(root, f"ctx:invalid-strip-{i}")


def test_valid_strip_h1_parameter_values(md_project):
    """Test all valid values of strip_h1 parameter."""
    root = md_project

    # Test all valid values for strip_h1
    valid_true_values = ["true", "1", "yes"]
    valid_false_values = ["false", "0", "no"]

    for value in valid_true_values:
        create_template(root, f"strip-true-{value}", f"""# Strip H1 True Test

${{md:docs/api, strip_h1:{value}}}
""")

        result = render_template(root, f"ctx:strip-true-{value}")
        # strip_h1:true - H1 should be removed
        assert "### API Reference" not in result  # H1 removed
        assert "## Authentication" in result       # H2 remained H2 (contextual analysis not applied)

    for value in valid_false_values:
        create_template(root, f"strip-false-{value}", f"""# Strip H1 False Test

${{md:docs/api, strip_h1:{value}}}
""")

        result = render_template(root, f"ctx:strip-false-{value}")
        # strip_h1:false - H1 should be preserved
        assert "## API Reference" in result      # H1 preserved as H2 (contextual analysis not applied)
        assert "### Authentication" in result     # H2 became H3


def test_parameter_parsing_with_spaces(md_project):
    """Test parameter parsing with different spaces."""
    root = md_project

    create_template(root, "spaces-test", """# Spaces Test

## No spaces
${md:docs/api,level:3,strip_h1:true}

## With spaces
${md:docs/guide, level:4, strip_h1:false}

## Mixed spaces
${md:docs/changelog,level:5, strip_h1: true}
""")

    result = render_template(root, "ctx:spaces-test")

    # All variants should work correctly
    assert "### Authentication" in result    # api: level:3, strip_h1:true
    assert "#### User Guide" in result       # guide: level:4, strip_h1:false
    assert "##### v1.0.0" in result          # changelog: level:5, strip_h1:true


def test_unknown_parameter_error(md_project):
    """Test handling of unknown parameters."""
    root = md_project

    create_template(root, "unknown-param-test", """# Unknown Parameter Test

${md:docs/api, level:3, unknown_param:value, strip_h1:true}
""")

    # Unknown parameters should raise error or be ignored
    with pytest.raises(Exception):  # ValueError about unknown parameter
        render_template(root, "ctx:unknown-param-test")


def test_parameter_case_sensitivity(md_project):
    """Test case sensitivity in parameters."""
    root = md_project

    create_template(root, "case-test", """# Case Sensitivity Test

${md:docs/api, Level:3, Strip_H1:True}
""")

    # Parameters should be case-sensitive
    with pytest.raises(Exception):  # Unknown parameters Level, Strip_H1
        render_template(root, "ctx:case-test")


@pytest.mark.parametrize("level,expected_h1,expected_h2", [
    (1, "# API Reference", "## Authentication"),
    (2, "## API Reference", "### Authentication"),
    (3, "### API Reference", "#### Authentication"),
    (4, "#### API Reference", "##### Authentication"),
    (5, "##### API Reference", "###### Authentication"),
    (6, "###### API Reference", "###### Authentication"),  # H2 cannot become H7
])
def test_level_parameter_parametrized(md_project, level, expected_h1, expected_h2):
    """Parametrized test for different level values."""
    root = md_project

    create_template(root, f"param-level-{level}", f"""# Level {level} Test

${{md:docs/api, level:{level}, strip_h1:false}}
""")

    result = render_template(root, f"ctx:param-level-{level}")

    assert expected_h1 in result
    # For level:6 H2 may not transform to H7 (check separately)
    if level < 6:
        assert expected_h2 in result


@pytest.mark.parametrize("strip_h1,should_have_h1", [
    (True, False),   # strip_h1:true - should not have H1
    (False, True),   # strip_h1:false - should have H1
])
def test_strip_h1_parameter_parametrized(md_project, strip_h1, should_have_h1):
    """Parametrized test for strip_h1."""
    root = md_project

    create_template(root, f"param-strip-{strip_h1}", f"""# Strip H1 Test

${{md:docs/api, level:3, strip_h1:{str(strip_h1).lower()}}}
""")

    result = render_template(root, f"ctx:param-strip-{strip_h1}")

    has_api_h3 = "### API Reference" in result
    assert has_api_h3 == should_have_h1, f"Expected H1 presence: {should_have_h1}, got: {has_api_h3}"