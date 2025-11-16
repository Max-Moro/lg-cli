"""
Tests for contextual heading analysis for markdown placeholders.

Implements logic according to requirements:
- strip_h1=true when placeholders are separated by parent template headings
- strip_h1=false when placeholders form a continuous chain
- max_heading_level is determined by nearest parent heading level
"""

from __future__ import annotations

from .conftest import md_project, create_template, render_template


def extract_heading_level(text: str, heading_text: str) -> int | None:
    """
    Extracts the exact heading level from text.

    Args:
        text: Text to search in
        heading_text: Heading text (without #)

    Returns:
        Heading level (number of #) or None if not found
    """
    heading_text = heading_text.strip()

    for line in text.split('\n'):
        line_stripped = line.strip()

        # Check if line starts with #
        if line_stripped.startswith('#'):
            # Count # at the beginning
            level = 0
            for char in line_stripped:
                if char == '#':
                    level += 1
                else:
                    break

            # Get heading text (after # and spaces)
            title_part = line_stripped[level:].strip()

            # Compare with searched heading
            if title_part == heading_text:
                return level

    return None


def assert_heading_level(result: str, heading_text: str, expected_level: int):
    """
    Checks the exact heading level in the result.

    Args:
        result: Rendering result
        heading_text: Heading text (without #)
        expected_level: Expected heading level
    """
    actual_level = extract_heading_level(result, heading_text)
    assert actual_level == expected_level, (
        f"Expected heading '{heading_text}' to be level {expected_level}, "
        f"but found level {actual_level}. Full result:\n{result}"
    )


def assert_heading_not_present(result: str, heading_text: str):
    """
    Checks that heading is not present in result.

    Args:
        result: Rendering result
        heading_text: Heading text to check
    """
    actual_level = extract_heading_level(result, heading_text)
    assert actual_level is None, (
        f"Heading '{heading_text}' should not be present, but found at level {actual_level}. "
        f"Full result:\n{result}"
    )


# ===== Tests for strip_h1=true (placeholders separated by headings) =====

def test_placeholders_separated_by_headings_strip_h1_true(md_project):
    """
    Test case strip_h1=true: placeholders are separated by parent template headings.

    Corresponds to first example from requirements:
    ### Templates, contexts and cascading inclusions
    ${md:docs/templates}
    ### Markdown working guide
    ${md:docs/markdown}
    """
    root = md_project

    create_template(root, "separated-placeholders", """# Listing Generator

## Extended documentation

### Templates, contexts and cascading inclusions

${md:docs/api}

### Markdown working guide

${md:docs/guide}

### Language adapters

${md:docs/changelog}

## License
""")

    result = render_template(root, "ctx:separated-placeholders")

    # Placeholders are separated by H3 headings of parent template
    # Therefore strip_h1=true, max_heading_level=4 (H3+1)

    # H1 headings from files should be removed
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    # changelog.md has no H1, so nothing is removed

    # H2 headings from files become H4 (under H3 of parent template)
    assert_heading_level(result, "Authentication", 4)  # from api.md
    assert_heading_level(result, "Endpoints", 4)       # from api.md
    assert_heading_level(result, "Installation", 4)    # from guide.md
    assert_heading_level(result, "Usage", 4)           # from guide.md
    assert_heading_level(result, "v1.0.0", 4)         # from changelog.md
    assert_heading_level(result, "v0.9.0", 4)         # from changelog.md

    # Headings from parent template should remain in their places
    assert_heading_level(result, "Listing Generator", 1)
    assert_heading_level(result, "Extended documentation", 2)
    assert_heading_level(result, "Templates, contexts and cascading inclusions", 3)
    assert_heading_level(result, "Markdown working guide", 3)
    assert_heading_level(result, "Language adapters", 3)
    assert_heading_level(result, "License", 2)


def test_placeholders_separated_by_h2_headings(md_project):
    """
    Test case strip_h1=true with H2 headings as separators.
    """
    root = md_project

    create_template(root, "h2-separated", """# Project Documentation

## API Reference Section

${md:docs/api}

## User Guide Section

${md:docs/guide}

## Changelog Section

${md:docs/changelog}

## Summary
""")

    result = render_template(root, "ctx:h2-separated")

    # Placeholders are separated by H2 headings
    # strip_h1=true, max_heading_level=3 (H2+1)

    # H1 headings from files are removed
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")

    # H2 headings from files become H3
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)
    assert_heading_level(result, "v1.0.0", 3)


# ===== Tests for strip_h1=false (placeholders form a chain) =====

def test_placeholders_continuous_chain_strip_h1_false(md_project):
    """
    Test case strip_h1=false: placeholders form a continuous chain.

    Corresponds to second example from requirements:
    ## Extended documentation
    ${md:docs/templates}
    ${md:docs/markdown}
    ${md:docs/markdown}
    """
    root = md_project

    create_template(root, "continuous-chain", """# Listing Generator

## Extended documentation

${md:docs/api}

${md:docs/guide}

${md:docs/changelog}

## License
""")

    result = render_template(root, "ctx:continuous-chain")

    # Placeholders form a continuous chain under H2
    # strip_h1=false, max_heading_level=3 (H2+1)

    # H1 headings from files are preserved, but become H3
    assert_heading_level(result, "API Reference", 3)   # was H1, became H3
    assert_heading_level(result, "User Guide", 3)      # was H1, became H3
    # changelog.md has no H1

    # H2 headings from files become H4
    assert_heading_level(result, "Authentication", 4)  # was H2, became H4
    assert_heading_level(result, "Installation", 4)    # was H2, became H4
    # But headings from changelog.md (which has no H1) are also normalized as H2->H3
    assert_heading_level(result, "v1.0.0", 3)         # was H2, became H3 (file without H1)

    # Headings from parent template are preserved
    assert_heading_level(result, "Listing Generator", 1)
    assert_heading_level(result, "Extended documentation", 2)
    assert_heading_level(result, "License", 2)


def test_continuous_chain_starting_immediately(md_project):
    """
    Test continuous chain starting immediately after section heading.
    """
    root = md_project

    create_template(root, "immediate-chain", """# Main Document

## Documentation Section
${md:docs/api}
${md:docs/guide}
${md:docs/changelog}

## Other Section

Some other content.
""")

    result = render_template(root, "ctx:immediate-chain")

    # Placeholders form a chain under H2
    # strip_h1=false, max_heading_level=3

    # H1 headings are preserved at level H3
    assert_heading_level(result, "API Reference", 3)
    assert_heading_level(result, "User Guide", 3)

    # H2 headings at level H4
    assert_heading_level(result, "Authentication", 4)
    assert_heading_level(result, "Installation", 4)


def test_mixed_content_between_placeholders_breaks_chain(md_project):
    """
    Test that arbitrary content between placeholders breaks the chain.

    If there is other content between placeholders, this may change the logic.
    Let's clarify the behavior: text between placeholders does NOT break the chain,
    only headings break it.
    """
    root = md_project

    create_template(root, "mixed-content", """# Main Document

## Documentation Section

${md:docs/api}

Some explanatory text between placeholders.

${md:docs/guide}

More text.

${md:docs/changelog}

## Other Section
""")

    result = render_template(root, "ctx:mixed-content")

    # Text between placeholders does NOT break the chain
    # strip_h1=false, max_heading_level=3

    assert_heading_level(result, "API Reference", 3)
    assert_heading_level(result, "User Guide", 3)


def test_clear_demonstration_of_chain_logic_fix(md_project):
    """
    Clear demonstration of chain logic fix.

    Shows the difference between cases:
    1) Placeholders separated by headings → strip_h1=true
    2) Placeholders form a chain (even when placeholders are in headings) → strip_h1=false
    """
    root = md_project

    # Case 1: placeholders separated by headings
    create_template(root, "separated", """# Documentation

## API Section
${md:docs/api}

## Guide Section
${md:docs/guide}
""")

    separated_result = render_template(root, "ctx:separated")

    # Placeholders separated → strip_h1=true
    assert_heading_not_present(separated_result, "API Reference")
    assert_heading_not_present(separated_result, "User Guide")
    assert_heading_level(separated_result, "Authentication", 3)  # H2→H3
    assert_heading_level(separated_result, "Installation", 3)    # H2→H3

    # Case 2: placeholders form a chain + placeholder in heading
    create_template(root, "chained", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}

## ${md:README}
""")

    chained_result = render_template(root, "ctx:chained")

    # Placeholders api and guide form a chain → strip_h1=false
    assert_heading_level(chained_result, "API Reference", 3)    # H1→H3 (preserved)
    assert_heading_level(chained_result, "User Guide", 3)       # H1→H3 (preserved)
    assert_heading_level(chained_result, "Authentication", 4)   # H2→H4
    assert_heading_level(chained_result, "Installation", 4)     # H2→H4

    # Placeholder in heading does not affect the chain of regular placeholders


# ===== Tests for max_heading_level determination =====

def test_max_heading_level_from_h4_context(md_project):
    """
    Test automatic determination of max_heading_level=5 when inserting under H4.
    """
    root = md_project

    create_template(root, "h4-context", """# Main

## Part 1

### Chapter 1

#### Section: API Documentation

${md:docs/api}

#### Another Section

Some content.
""")

    result = render_template(root, "ctx:h4-context")

    # Placeholder under H4, separated from other headings
    # strip_h1=true, max_heading_level=5 (H4+1)

    # H1 removed
    assert_heading_not_present(result, "API Reference")

    # H2 headings become H5
    assert_heading_level(result, "Authentication", 5)
    assert_heading_level(result, "Endpoints", 5)


def test_max_heading_level_limits_at_h6(md_project):
    """
    Test limiting maximum heading level to H6.
    """
    root = md_project

    create_template(root, "h6-limit", """# Level 1

## Level 2

### Level 3

#### Level 4

##### Level 5

###### Level 6 Section

${md:docs/api}
""")

    result = render_template(root, "ctx:h6-limit")

    # When trying to set max_heading_level=7, system should limit to H6
    # or apply other logic to prevent invalid headings

    lines = result.split('\n')
    invalid_headings = [line for line in lines if line.startswith('#######')]
    assert len(invalid_headings) == 0, f"Found invalid H7+ headings: {invalid_headings}"

    # File contents should be present
    assert "Authentication" in result
    assert "Endpoints" in result


# ===== Tests for placeholders inside headings =====

def test_placeholder_inside_heading_replaces_heading_text(md_project):
    """
    Test placeholder inside heading - replaces heading text.

    ### ${md:docs/api}

    Here H1 from api.md becomes the content of heading H3.
    """
    root = md_project

    create_template(root, "inline-heading", """# Listing Generator

## Extended documentation

### ${md:docs/api}

### ${md:docs/guide}

## Conclusion
""")

    result = render_template(root, "ctx:inline-heading")

    # Placeholders inside H3 headings
    # H1 from files replaces the content of H3 headings
    # strip_h1=true (H1 used for heading), max_heading_level=4

    assert_heading_level(result, "API Reference", 3)   # H1 from api.md became H3
    assert_heading_level(result, "User Guide", 3)      # H1 from guide.md became H3

    # H2 headings from files become H4
    assert_heading_level(result, "Authentication", 4)
    assert_heading_level(result, "Installation", 4)


def test_placeholder_inside_h2_heading(md_project):
    """
    Test placeholder inside H2 heading.
    """
    root = md_project

    create_template(root, "h2-inline", """# Project Manual

## API: ${md:docs/api}

## Guide: ${md:docs/guide}

## Summary
""")

    result = render_template(root, "ctx:h2-inline")

    # H1 from files becomes part of H2 headings
    assert_heading_level(result, "API: API Reference", 2)
    assert_heading_level(result, "Guide: User Guide", 2)

    # H2 headings from files become H3
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


# ===== Tests for explicit parameters =====

def test_explicit_parameters_override_contextual_analysis(md_project):
    """
    Test that explicit parameters override contextual analysis.
    """
    root = md_project

    create_template(root, "explicit-override", """# Main

## Section

### Subsection

${md:docs/api, level:2, strip_h1:false}
""")

    result = render_template(root, "ctx:explicit-override")

    # Explicit parameters should override automatic analysis
    # level:2 means max_heading_level=2
    # strip_h1:false means preserve H1

    assert_heading_level(result, "API Reference", 2)    # H1→H2 (explicitly set)
    assert_heading_level(result, "Authentication", 3)   # H2→H3


def test_explicit_strip_h1_true_overrides_chain_logic(md_project):
    """
    Test that explicit strip_h1:true overrides chain logic.
    """
    root = md_project

    create_template(root, "explicit-strip", """# Main

## Documentation

${md:docs/api, strip_h1:true}

${md:docs/guide, strip_h1:true}
""")

    result = render_template(root, "ctx:explicit-strip")

    # Despite placeholder chain, explicit strip_h1:true should work
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")

    # Content starts with H3 (under H2)
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


# ===== Tests for cases without headings in template =====

def test_single_placeholder_no_headings_in_template(md_project):
    """
    Test simplest case: only placeholder without headings in template.

    ${md:README}

    Should be inserted as a top-level document:
    - strip_h1=false (H1 is preserved)
    - heading_level=1 (top-level document)
    """
    root = md_project

    create_template(root, "single-no-headings", """${md:README}""")

    result = render_template(root, "ctx:single-no-headings")

    # Document is inserted as root
    # H1 should be preserved at level H1
    assert_heading_level(result, "Main Project", 1)

    # H2 headings remain H2
    assert_heading_level(result, "Features", 2)


def test_placeholder_with_horizontal_rule_no_headings(md_project):
    """
    Test case with horizontal rule, but without headings.

    ${md:README}

    ---

    ${md:docs/guide}

    Both documents should be inserted as root documents:
    - strip_h1=false (H1 is preserved)
    - heading_level=1 (top-level documents)
    """
    root = md_project

    create_template(root, "hr-no-headings", """${md:README}

---

${md:docs/guide}""")

    result = render_template(root, "ctx:hr-no-headings")

    # Both documents are inserted as root, despite horizontal rule
    # H1 headings are preserved at level H1
    assert_heading_level(result, "Main Project", 1)
    assert_heading_level(result, "User Guide", 1)

    # H2 headings remain H2
    assert_heading_level(result, "Features", 2)
    assert_heading_level(result, "Installation", 2)


def test_isolated_placeholder_with_unrelated_heading(md_project):
    """
    Test case with isolated placeholder and unrelated heading after it.

    ${md:README}

    ---

    # License

    Placeholder is isolated and should not be related to "License" heading,
    which comes after the horizontal rule:
    - strip_h1=false (H1 from README is preserved, since placeholder is not in a chain)
    - heading_level=1 (top-level document, since there are no parent headings)
    - "License" heading should remain at H1 level (after horizontal rule)
    """
    root = md_project

    create_template(root, "isolated-unrelated", """${md:README}

---

# License

Some license text here.""")

    result = render_template(root, "ctx:isolated-unrelated")

    # Placeholder is inserted as root document
    # H1 from README should be preserved (strip_h1=false for isolated placeholder)
    assert_heading_level(result, "Main Project", 1)
    assert_heading_level(result, "Features", 2)


def test_multiple_placeholders_no_headings_with_text(md_project):
    """
    Test case with multiple placeholders and text, but without headings.

    ${md:docs/api}

    Some text between documents.

    ${md:docs/guide}

    Documents form a chain (no heading separators), but they should be inserted
    as top-level documents, because there are no headings in the surrounding context.
    """
    root = md_project

    create_template(root, "multiple-no-headings", """${md:docs/api}

Some text between documents.

${md:docs/guide}""")

    result = render_template(root, "ctx:multiple-no-headings")

    # Documents form a chain, but are inserted as root
    # strip_h1=false (H1 is preserved), heading_level=1
    assert_heading_level(result, "API Reference", 1)
    assert_heading_level(result, "User Guide", 1)

    # H2 headings remain H2
    assert_heading_level(result, "Authentication", 2)
    assert_heading_level(result, "Installation", 2)


def test_placeholder_with_only_text_before_and_after(md_project):
    """
    Test placeholder with regular text before and after, without headings.

    This is some introductory text.

    ${md:docs/api}

    This is some concluding text.
    """
    root = md_project

    create_template(root, "text-around", """This is some introductory text.

${md:docs/api}

This is some concluding text.""")

    result = render_template(root, "ctx:text-around")

    # Document is inserted as root (no parent headings)
    assert_heading_level(result, "API Reference", 1)
    assert_heading_level(result, "Authentication", 2)

# ===== Special cases =====

def test_setext_headings_in_contextual_analysis(md_project):
    """
    Test contextual analysis with Setext headings (underlines).
    """
    root = md_project

    create_template(root, "setext-test", """Project Guide
=============

API Documentation
-----------------

${md:docs/api}

User Guide
----------

${md:docs/guide}
""")

    result = render_template(root, "ctx:setext-test")

    # Setext headings: "Project Guide" = H1, "API Documentation" = H2
    # Placeholders are separated by H2 headings
    # strip_h1=true, max_heading_level=3

    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")

    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


def test_fenced_blocks_ignored_in_contextual_analysis(md_project):
    """
    Test that headings in fenced blocks are ignored during context analysis.
    """
    root = md_project

    create_template(root, "fenced-ignore", """# Documentation

## Configuration Example

```yaml
# This is not a real heading
## This is also not a heading
### Neither is this
```

### Actual Section

${md:docs/api}

### Another Section

More content.
""")

    result = render_template(root, "ctx:fenced-ignore")

    # Should analyze only real headings, ignoring ```-blocks
    # Placeholder is separated by H3 headings
    # strip_h1=true, max_heading_level=4

    assert_heading_not_present(result, "API Reference")
    assert_heading_level(result, "Authentication", 4)
