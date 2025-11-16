"""
Tests for contextual heading analysis with horizontal rules.
"""

from __future__ import annotations

from tests.md_placeholders.conftest import md_project, create_template, render_template
from tests.md_placeholders.test_contextual_analysis import (
    extract_heading_level, assert_heading_level, assert_heading_not_present
)


# ===== Tests for main scenario with horizontal rules =====

def test_horizontal_rule_resets_context_to_level_1(md_project):
    """
    Test that horizontal rule resets heading context to level 1.
    """
    root = md_project

    create_template(root, "horizontal-rule-reset", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")

    result = render_template(root, "ctx:horizontal-rule-reset")

    # Before horizontal rule: placeholders form chain under H2
    # strip_h1=FALSE (chain), max_heading_level=3 (H2+1)
    # H1 headings preserved as H3, H2+ increased by 2
    assert_heading_level(result, "API Reference", 3)    # H1→H3 (chain, preserved)
    assert_heading_level(result, "User Guide", 3)       # H1→H3 (chain, preserved)
    assert_heading_level(result, "Authentication", 4)   # H2→H4 (increased by 2)
    assert_heading_level(result, "Installation", 4)     # H2→H4 (increased by 2)

    # After horizontal rule: context reset to level 1
    # strip_h1=false (no parent heading), max_heading_level=1
    assert_heading_level(result, "Main Project", 1)     # H1→H1 (original level)
    assert_heading_level(result, "Features", 2)         # H2→H2 (original level)


def test_multiple_horizontal_rules_create_isolated_sections(md_project):
    """
    Test that multiple horizontal rules create isolated sections.
    """
    root = md_project

    create_template(root, "multiple-rules", """# Documentation

## Section A
${md:docs/api}

---

## Section B
${md:docs/guide}

---

## Section C
${md:README}
""")

    result = render_template(root, "ctx:multiple-rules")

    # Each placeholder is isolated by H2 headings
    # strip_h1=true (separated by headings), max_heading_level=3 (H2+1)

    # api.md in Section A
    assert_heading_not_present(result, "API Reference")      # H1 removed
    assert_heading_level(result, "Authentication", 3)        # H2→H3

    # guide.md in Section B
    assert_heading_not_present(result, "User Guide")         # H1 removed
    assert_heading_level(result, "Installation", 3)          # H2→H3

    # README.md in Section C
    assert_heading_not_present(result, "Main Project")       # H1 removed
    assert_heading_level(result, "Features", 3)              # H2→H3


def test_horizontal_rule_different_formats(md_project):
    """
    Test different horizontal rule formats: ---, ***, ___.
    """
    root = md_project

    create_template(root, "rule-formats", """# Documentation

## Part 1
${md:docs/api}

---

${md:docs/guide}

***

${md:docs/changelog}

___

${md:README}
""")

    result = render_template(root, "ctx:rule-formats")

    # All horizontal rule formats should work the same
    # Each placeholder is isolated, context reset to level 1

    # After first rule (---)
    assert_heading_level(result, "User Guide", 1)        # H1→H1 (root)
    assert_heading_level(result, "Installation", 2)      # H2→H2 (root)

    # After second rule (***)
    assert_heading_level(result, "v1.0.0", 1)           # H2→H1 (no H1 in file, H2 becomes root)
    assert_heading_level(result, "v0.9.0", 1)           # H2→H1

    # After third rule (___)
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (root)
    assert_heading_level(result, "Features", 2)          # H2→H2 (root)


# ===== Tests for breaking chains with horizontal rules =====

def test_horizontal_rule_breaks_placeholder_chain(md_project):
    """
    Test that horizontal rule breaks placeholder chain.

    Before rule: chain (strip_h1=false)
    After rule: isolated placeholder (strip_h1=false, but level 1)
    """
    root = md_project

    create_template(root, "chain-break", """# Documentation

## Connected Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")

    result = render_template(root, "ctx:chain-break")

    # Before rule: chain of placeholders under H2
    # strip_h1=FALSE (chain), max_heading_level=3
    # H1 headings preserved as H3, H2+ increased by 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (chain, preserved)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (chain, preserved)
    assert_heading_level(result, "Authentication", 4)    # H2→H4 (increased by 2)

    # After rule: isolated placeholder, context reset
    # strip_h1=false (no parent heading), max_heading_level=1
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (root)
    assert_heading_level(result, "Features", 2)          # H2→H2 (root)


def test_chain_before_and_after_horizontal_rule(md_project):
    """
    Test placeholder chains before and after horizontal rule.
    """
    root = md_project

    create_template(root, "chains-separated", """# Main Document

## Before Rule Section
${md:docs/api}
${md:docs/guide}

---

## After Rule Section
${md:docs/changelog}
${md:README}
""")

    result = render_template(root, "ctx:chains-separated")

    # Before horizontal rule: chain under H2
    # strip_h1=FALSE (chain), max_heading_level=3
    # H1 headings preserved as H3, H2+ increased by 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (chain, preserved)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (chain, preserved)

    # After horizontal rule: new chain under H2 (but with new context)
    # strip_h1=FALSE (chain), max_heading_level=3
    # changelog.md has no H1, README.md has H1 and it's preserved
    assert_heading_level(result, "v1.0.0", 3)           # H2→H3 (changelog without H1, increased by 1)
    assert_heading_level(result, "Main Project", 3)      # H1→H3 (chain, preserved)


# ===== Tests for interaction with inline placeholders =====

def test_horizontal_rule_with_placeholder_in_heading(md_project):
    """
    Test horizontal rule in combination with placeholders inside headings.
    """
    root = md_project

    create_template(root, "rule-inline-heading", """# Project Documentation

## Normal Section
${md:docs/api}

---

## ${md:docs/guide}

Some additional content.

## Regular Section Again
${md:README}
""")

    result = render_template(root, "ctx:rule-inline-heading")

    # Before rule: normal placeholder under H2
    assert_heading_not_present(result, "API Reference")  # H1 removed (separated)
    assert_heading_level(result, "Authentication", 3)    # H2→H3

    # After rule: placeholder in H2 heading
    assert_heading_level(result, "User Guide", 2)        # H1 replaced H2 content
    assert_heading_level(result, "Installation", 3)      # H2→H3 (under inline heading)

    # Another placeholder after inline heading
    assert_heading_not_present(result, "Main Project")   # H1 removed (separated)
    assert_heading_level(result, "Features", 3)          # H2→H3


# ===== Edge case tests =====

def test_horizontal_rule_at_document_start(md_project):
    """
    Test horizontal rule at document start.
    """
    root = md_project

    create_template(root, "rule-at-start", """---

${md:README}

## Additional Section
${md:docs/api}
""")

    result = render_template(root, "ctx:rule-at-start")

    # README at the very beginning after rule: root level
    assert_heading_level(result, "Main Project", 1)      # H1→H1
    assert_heading_level(result, "Features", 2)          # H2→H2

    # api.md under H2: separated by heading
    assert_heading_not_present(result, "API Reference")  # H1 removed
    assert_heading_level(result, "Authentication", 3)    # H2→H3


def test_horizontal_rule_at_document_end(md_project):
    """
    Test horizontal rule at document end.
    """
    root = md_project

    create_template(root, "rule-at-end", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}

---
""")

    result = render_template(root, "ctx:rule-at-end")

    # Chain of placeholders before rule should work normally
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (chain)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (chain)
    assert_heading_level(result, "Authentication", 4)    # H2→H4
    assert_heading_level(result, "Installation", 4)      # H2→H4


def test_horizontal_rule_inside_fenced_block_ignored(md_project):
    """
    Test that horizontal rules inside fenced blocks are ignored.
    """
    root = md_project

    create_template(root, "rule-in-fenced", """# Documentation

## Code Example

```markdown
# Sample Document

---

This is not a real horizontal rule.
```

## Continuous Section
${md:docs/api}
${md:docs/guide}

---

${md:README}
""")

    result = render_template(root, "ctx:rule-in-fenced")

    # Rule in fenced block should not affect analysis
    # api.md and guide.md should form chain under H2
    # strip_h1=FALSE (chain), max_heading_level=3
    # H1 headings preserved as H3, H2+ increased by 2
    assert_heading_level(result, "API Reference", 3)     # H1→H3 (chain, preserved)
    assert_heading_level(result, "User Guide", 3)        # H1→H3 (chain, preserved)

    # README after real rule: reset context
    # strip_h1=false (no parent heading), max_heading_level=1
    assert_heading_level(result, "Main Project", 1)      # H1→H1 (root)
    assert_heading_level(result, "Features", 2)          # H2→H2 (root)


# ===== Tests for backward compatibility =====

def test_horizontal_rule_preserves_existing_logic_for_regular_cases(md_project):
    """
    Test that adding horizontal rule support doesn't break existing logic.

    Templates without horizontal rules should work as before.
    """
    root = md_project

    # Case 1: separated by headings (should be strip_h1=true)
    create_template(root, "backward-compat-separated", """# Documentation

## API Section
${md:docs/api}

## Guide Section
${md:docs/guide}
""")

    separated_result = render_template(root, "ctx:backward-compat-separated")

    # Placeholders separated → strip_h1=true
    assert_heading_not_present(separated_result, "API Reference")
    assert_heading_not_present(separated_result, "User Guide")
    assert_heading_level(separated_result, "Authentication", 3)
    assert_heading_level(separated_result, "Installation", 3)

    # Case 2: continuous chain (should be strip_h1=false)
    create_template(root, "backward-compat-chain", """# Documentation

## Main Section
${md:docs/api}
${md:docs/guide}
""")

    chain_result = render_template(root, "ctx:backward-compat-chain")

    # Placeholders form chain → strip_h1=false
    assert_heading_level(chain_result, "API Reference", 3)    # H1→H3 (preserved)
    assert_heading_level(chain_result, "User Guide", 3)       # H1→H3 (preserved)
    assert_heading_level(chain_result, "Authentication", 4)   # H2→H4
    assert_heading_level(chain_result, "Installation", 4)     # H2→H4


def test_explicit_parameters_still_override_horizontal_rule_logic(md_project):
    """
    Test that explicit parameters still override horizontal rule logic.
    """
    root = md_project

    create_template(root, "explicit-override-with-rule", """# Documentation

## Section A
${md:docs/api}

---

${md:README, level:3, strip_h1:true}
""")

    result = render_template(root, "ctx:explicit-override-with-rule")

    # Before rule: normal logic
    assert_heading_not_present(result, "API Reference")  # H1 removed (separated)
    assert_heading_level(result, "Authentication", 3)    # H2→H3

    # After rule: explicit parameters override context reset logic
    assert_heading_not_present(result, "Main Project")   # strip_h1:true forced
    assert_heading_level(result, "Features", 3)          # level:3 forced (H2→H3)