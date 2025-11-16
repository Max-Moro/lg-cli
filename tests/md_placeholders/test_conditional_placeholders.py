"""
Tests for conditional markdown placeholders.

Checks the functionality of conditional document inclusion:
- ${md:file, if:tag:name} for inclusion by active tags
- Different condition types (tag:, TAGSET:, NOT)
- Condition combinations with other parameters
- Handling inactive conditions
"""

from __future__ import annotations

import pytest

from .conftest import (
    adaptive_md_project, create_template, render_template, 
    make_run_options, write_markdown
)


def test_conditional_md_placeholder_basic_tag(adaptive_md_project):
    """Test basic conditional inclusion by tag."""
    root = adaptive_md_project

    create_template(root, "conditional-basic-test", """# Conditional Test

## Cloud Deployment (only if cloud tag active)
${md:deployment/cloud, if:tag:cloud}

## On-Premises Deployment (only if onprem tag active)
${md:deployment/onprem, if:tag:onprem}

## Always Visible
${md:basic/intro}
""")

    # Test without active tags
    result1 = render_template(root, "ctx:conditional-basic-test")
    assert "Instructions for cloud deployment." not in result1
    assert "Instructions for on-premises deployment." not in result1
    assert "Basic introduction to the project." in result1  # always visible

    # Test with active cloud tag
    options_cloud = make_run_options(extra_tags={"cloud"})
    result2 = render_template(root, "ctx:conditional-basic-test", options_cloud)
    assert "Instructions for cloud deployment." in result2
    assert "Instructions for on-premises deployment." not in result2
    assert "Basic introduction to the project." in result2

    # Test with active onprem tag
    options_onprem = make_run_options(extra_tags={"onprem"})
    result3 = render_template(root, "ctx:conditional-basic-test", options_onprem)
    assert "Instructions for cloud deployment." not in result3
    assert "Instructions for on-premises deployment." in result3
    assert "Basic introduction to the project." in result3


def test_conditional_md_placeholder_with_not_condition(adaptive_md_project):
    """Test conditional inclusion with NOT negation."""
    root = adaptive_md_project

    create_template(root, "conditional-not-test", """# NOT Condition Test

## Basic Docs (when not cloud)
${md:basic/intro, if:NOT tag:cloud}

## Cloud Docs (when cloud)
${md:deployment/cloud, if:tag:cloud}
""")

    # Without tags: NOT tag:cloud = true
    result1 = render_template(root, "ctx:conditional-not-test")
    assert "Basic introduction to the project." in result1
    assert "Instructions for cloud deployment." not in result1

    # With cloud tag: NOT tag:cloud = false
    options_cloud = make_run_options(extra_tags={"cloud"})
    result2 = render_template(root, "ctx:conditional-not-test", options_cloud)
    assert "Basic introduction to the project." not in result2
    assert "Instructions for cloud deployment." in result2


def test_conditional_md_placeholder_complex_conditions(adaptive_md_project):
    """Test complex conditions with AND/OR."""
    root = adaptive_md_project

    create_template(root, "conditional-complex-test", """# Complex Conditions Test

## Cloud AND Basic
${md:deployment/cloud, if:tag:cloud AND tag:basic}

## Cloud OR OnPrem
${md:basic/intro, if:tag:cloud OR tag:onprem}

## NOT (Cloud AND OnPrem)
${md:deployment/onprem, if:NOT (tag:cloud AND tag:onprem)}
""")

    # Test cloud AND basic (both tags)
    options_both = make_run_options(extra_tags={"cloud", "basic"})
    result1 = render_template(root, "ctx:conditional-complex-test", options_both)
    assert "Instructions for cloud deployment." in result1  # cloud AND basic = true
    assert "Basic introduction to the project." in result1   # cloud OR onprem = true
    assert "Instructions for on-premises deployment." in result1  # NOT (cloud AND onprem) = NOT(true AND false) = NOT false = true

    # Test only cloud (without basic)
    options_cloud = make_run_options(extra_tags={"cloud"})
    result2 = render_template(root, "ctx:conditional-complex-test", options_cloud)
    assert "Instructions for cloud deployment." not in result2  # cloud AND basic = false
    assert "Basic introduction to the project." in result2      # cloud OR onprem = true
    assert "Instructions for on-premises deployment." in result2  # NOT (cloud AND onprem) = true

    # Test without tags
    result3 = render_template(root, "ctx:conditional-complex-test")
    assert "Instructions for cloud deployment." not in result3  # cloud AND basic = false
    assert "Basic introduction to the project." not in result3  # cloud OR onprem = false
    assert "Instructions for on-premises deployment." in result3  # NOT (cloud AND onprem) = true


def test_conditional_md_placeholder_with_parameters(adaptive_md_project):
    """Test conditional placeholders in combination with explicit parameters."""
    root = adaptive_md_project

    create_template(root, "conditional-params-test", """# Conditional with Parameters

## Section A
### Cloud Deployment (level 4, strip H1)
${md:deployment/cloud, if:tag:cloud, level:4, strip_h1:true}

## Section B
### OnPrem Deployment (level 3, keep H1)
${md:deployment/onprem, if:tag:onprem, level:3, strip_h1:false}
""")

    # Enable cloud tag
    options_cloud = make_run_options(extra_tags={"cloud"})
    result1 = render_template(root, "ctx:conditional-params-test", options_cloud)

    # Check parameter application: level:4, strip_h1:true
    assert "#### AWS" in result1        # was H2, became H4
    assert "#### Azure" in result1      # was H2, became H4
    # H1 "Cloud Deployment" should be removed (strip_h1:true)
    h1_lines = [line for line in result1.split('\n') if line.strip() == "#### Cloud Deployment"]
    assert len(h1_lines) == 0  # H1 removed, didn't become H4

    # Enable onprem tag
    options_onprem = make_run_options(extra_tags={"onprem"})
    result2 = render_template(root, "ctx:conditional-params-test", options_onprem)

    # Check parameter application: level:3, strip_h1:false
    assert "### On-Premises Deployment" in result2  # H1 preserved, became H3
    assert "#### Requirements" in result2            # was H2, became H4


def test_conditional_md_placeholder_with_anchors(adaptive_md_project):
    """Test conditional placeholders with anchor links."""
    root = adaptive_md_project

    create_template(root, "conditional-anchor-test", """# Conditional Anchors Test

## Cloud AWS Section (only if cloud)
${md:deployment/cloud#AWS, if:tag:cloud}

## OnPrem Requirements (only if onprem)
${md:deployment/onprem#Requirements, if:tag:onprem}
""")

    # Enable cloud
    options_cloud = make_run_options(extra_tags={"cloud"})
    result1 = render_template(root, "ctx:conditional-anchor-test", options_cloud)

    assert "Use CloudFormation." in result1  # from AWS section
    assert "Docker" not in result1           # from Requirements section onprem

    # Enable onprem
    options_onprem = make_run_options(extra_tags={"onprem"})
    result2 = render_template(root, "ctx:conditional-anchor-test", options_onprem)

    assert "Use CloudFormation." not in result2  # from AWS section
    assert "Docker" in result2                   # from Requirements section


def test_conditional_md_placeholder_with_addressed_origins(adaptive_md_project):
    """Test conditional placeholders with addressed links."""
    root = adaptive_md_project

    # Create file in lg-cfg for addressed link @self:
    write_markdown(root / "lg-cfg" / "internal-cloud.md",
                  title="Internal Cloud Guide",
                  content="Internal deployment procedures for cloud.\n\n## Security\n\nSecurity considerations.")

    create_template(root, "conditional-addressed-test", """# Conditional Addressed Test

## External Cloud Guide (if cloud)
${md:deployment/cloud, if:tag:cloud}

## Internal Cloud Guide (if cloud)
${md@self:internal-cloud, if:tag:cloud}

## Basic Guide (always)
${md:basic/intro}
""")

    # Without tags
    result1 = render_template(root, "ctx:conditional-addressed-test")
    assert "Instructions for cloud deployment." not in result1  # external file
    assert "Internal deployment procedures" not in result1      # file from lg-cfg
    assert "Basic introduction to the project." in result1      # always

    # With cloud tag
    options_cloud = make_run_options(extra_tags={"cloud"})
    result2 = render_template(root, "ctx:conditional-addressed-test", options_cloud)
    assert "Instructions for cloud deployment." in result2  # external file
    assert "Internal deployment procedures" in result2      # file from lg-cfg
    assert "Basic introduction to the project." in result2  # always


def test_conditional_md_placeholder_tagset_conditions(adaptive_md_project):
    """Test TAGSET conditions for md-placeholders."""
    root = adaptive_md_project

    # Add tag-sets to configuration
    from .conftest import write
    write(root / "lg-cfg" / "tags.yaml", """
tag-sets:
  deployment-type:
    title: "Deployment types"
    tags:
      cloud:
        title: "Cloud deployment"
      onprem:
        title: "On-premises deployment"

tags:
  basic:
    title: "Basic documentation"
""")

    create_template(root, "conditional-tagset-test", """# TagSet Conditions Test

## Any Deployment Type Active
${md:basic/intro}

## Cloud Deployment Type
${md:deployment/cloud, if:TAGSET:deployment-type:cloud}

## OnPrem Deployment Type
${md:deployment/onprem, if:TAGSET:deployment-type:onprem}
""")

    # Without tags: TAGSET conditions are true (no tags from the set are active)
    result1 = render_template(root, "ctx:conditional-tagset-test")
    assert "Basic introduction to the project." in result1
    assert "Instructions for cloud deployment." in result1  # TAGSET:deployment-type:cloud = true
    assert "Instructions for on-premises deployment." in result1  # TAGSET:deployment-type:onprem = true

    # With active cloud tag
    options_cloud = make_run_options(extra_tags={"cloud"})
    result2 = render_template(root, "ctx:conditional-tagset-test", options_cloud)
    assert "Basic introduction to the project." in result2
    assert "Instructions for cloud deployment." in result2  # TAGSET:deployment-type:cloud = true
    assert "Instructions for on-premises deployment." not in result2  # TAGSET:deployment-type:onprem = false


def test_conditional_md_placeholder_error_invalid_condition(adaptive_md_project):
    """Test error handling for incorrect conditions."""
    root = adaptive_md_project

    test_cases = [
        "${md:basic/intro, if:invalid_syntax}",           # incorrect syntax
        "${md:basic/intro, if:tag:}",                     # empty tag name
        "${md:basic/intro, if:TAGSET:}",                  # empty tagset name
        "${md:basic/intro, if:tag:nonexistent AND}",      # incomplete expression
    ]

    for i, invalid_placeholder in enumerate(test_cases):
        create_template(root, f"invalid-condition-{i}", f"""# Invalid Condition Test

{invalid_placeholder}
""")

        with pytest.raises(Exception):  # condition parsing error
            render_template(root, f"ctx:invalid-condition-{i}")


def test_conditional_md_placeholder_multiple_conditions_same_file(adaptive_md_project):
    """Test multiple conditional placeholders for the same file."""
    root = adaptive_md_project

    create_template(root, "multiple-conditions-test", """# Multiple Conditions Test

## Cloud Guide (basic condition)
${md:deployment/cloud, if:tag:cloud}

## Cloud Guide Again (complex condition)
${md:deployment/cloud, if:tag:cloud AND NOT tag:onprem}

## Cloud Guide Third Time (with parameters)
${md:deployment/cloud, if:tag:cloud, level:5}
""")

    # Enable only cloud
    options_cloud = make_run_options(extra_tags={"cloud"})
    result = render_template(root, "ctx:multiple-conditions-test", options_cloud)

    # File should be included 3 times with different conditions/parameters
    assert result.count("Instructions for cloud deployment.") == 3
    assert result.count("Use CloudFormation.") >= 2  # could be more due to different levels


@pytest.mark.parametrize("tags,cloud_visible,onprem_visible", [
    (set(), False, False),           # without tags
    ({"cloud"}, True, False),        # only cloud
    ({"onprem"}, False, True),       # only onprem
    ({"cloud", "onprem"}, True, True), # both tags
    ({"basic"}, False, False),       # other tag
])
def test_conditional_md_placeholder_parametrized(adaptive_md_project, tags, cloud_visible, onprem_visible):
    """Parametrized test for conditional markdown placeholders."""
    root = adaptive_md_project

    create_template(root, "param-conditional-test", """# Parametrized Test

${md:deployment/cloud, if:tag:cloud}
${md:deployment/onprem, if:tag:onprem}
""")

    options = make_run_options(extra_tags=tags)
    result = render_template(root, "ctx:param-conditional-test", options)

    cloud_present = "Instructions for cloud deployment." in result
    onprem_present = "Instructions for on-premises deployment." in result

    assert cloud_present == cloud_visible, f"Cloud visibility mismatch for tags {tags}"
    assert onprem_present == onprem_visible, f"OnPrem visibility mismatch for tags {tags}"