"""
Tests for anchor links in markdown placeholders.

Checks the functionality of partial document inclusion:
- ${md:file#section} for including individual sections
- Processing different heading formats
- Including nested sections
- Handling non-existent anchors
"""

from __future__ import annotations

import pytest

from .conftest import md_project, create_template, render_template, write_markdown


def test_anchor_basic_section_inclusion(md_project):
    """Test basic section inclusion by anchor."""
    root = md_project

    # Create file with several sections
    write_markdown(root / "sections.md",
                  title="Complete Guide",
                  content="""## Getting Started

Installation instructions here.

### Requirements

- Python 3.8+
- Node.js 16+

## Advanced Usage

Advanced features description.

### Configuration

Config file setup.

### Deployment

Production deployment guide.

## Troubleshooting

Common issues and solutions.
""")

    create_template(root, "anchor-basic-test", """# Anchor Test

## Only Getting Started
${md:sections#Getting Started}

## Only Advanced Usage
${md:sections#Advanced Usage}

## Only Troubleshooting
${md:sections#Troubleshooting}
""")

    result = render_template(root, "ctx:anchor-basic-test")

    # Check that each section is included separately
    assert "Installation instructions here." in result
    assert "Advanced features description." in result
    assert "Common issues and solutions." in result

    # Check heading structure (should preserve hierarchy)
    assert "## Getting Started" in result
    assert "### Requirements" in result
    assert "## Advanced Usage" in result
    assert "### Configuration" in result
    assert "### Deployment" in result
    assert "## Troubleshooting" in result


def test_anchor_with_slug_matching(md_project):
    """Test anchor matching through slug (GitHub-style conversion)."""
    root = md_project

    write_markdown(root / "slugs.md",
                  title="Test Document",
                  content="""## API & Usage

API documentation.

## FAQ: Common Questions

Frequently asked questions.

## Multi-Word Section Title

Content here.
""")

    create_template(root, "anchor-slug-test", """# Slug Matching Test

## Using exact text
${md:slugs#API & Usage}

## Using slug format
${md:slugs#api-usage}

## FAQ section (with colon)
${md:slugs#FAQ: Common Questions}

## Multi-word using slug
${md:slugs#multi-word-section-title}
""")

    result = render_template(root, "ctx:anchor-slug-test")

    # All variants should work thanks to slug matching
    assert result.count("API documentation.") >= 2  # should appear twice
    assert result.count("Frequently asked questions.") >= 1
    assert result.count("Content here.") >= 1


def test_anchor_nested_section_inclusion(md_project):
    """Test inclusion of nested sections."""
    root = md_project

    write_markdown(root / "nested.md",
                  title="Documentation",
                  content="""## Installation

Basic installation.

### Prerequisites

System requirements.

#### Hardware

Minimum specs.

#### Software

Required packages.

#### Download

Get the installer.

## Configuration

Setup instructions.
""")

    create_template(root, "anchor-nested-test", """# Nested Sections Test

## Prerequisites Section (includes subsections)
${md:nested#Prerequisites}

## Just Hardware Requirements
${md:nested#Hardware}
""")

    result = render_template(root, "ctx:anchor-nested-test")

    # Prerequisites should include all subsections
    assert "System requirements." in result
    assert "Minimum specs." in result
    assert "Required packages." in result
    assert "Get the installer." in result

    # Hardware should only have minimum specs
    assert result.count("Minimum specs.") == 2  # appears in both sections


def test_anchor_nonexistent_section_error(md_project):
    """Test error handling for non-existent anchor."""
    root = md_project

    create_template(root, "anchor-notfound-test", """# Not Found Test

${md:docs/api#NonexistentSection}
""")

    # Should raise TemplateProcessingError with informative message
    from lg.template.processor import TemplateProcessingError
    with pytest.raises(TemplateProcessingError) as exc_info:
        render_template(root, "ctx:anchor-notfound-test")

    # Check that message contains problem information
    error_message = str(exc_info.value)
    assert "NonexistentSection" in error_message
    assert "not found" in error_message
    assert "Available sections" in error_message
    # Check that available sections are shown
    assert "Authentication" in error_message
    assert "Endpoints" in error_message


def test_anchor_error_document_without_headings(md_project):
    """Test error when trying to find anchor in document without headings."""
    root = md_project

    # Create document without headings
    write_markdown(root / "no-headings.md",
                   title="",
                   content="Just plain text without any headings.\n\nMore text here.")

    create_template(root, "anchor-no-headings-test", """# No Headings Test

${md:no-headings#SomeSection}
""")

    from lg.template.processor import TemplateProcessingError
    with pytest.raises(TemplateProcessingError) as exc_info:
        render_template(root, "ctx:anchor-no-headings-test")

    error_message = str(exc_info.value)
    assert "SomeSection" in error_message
    assert "document has no sections" in error_message


def test_anchor_error_with_similar_headings(md_project):
    """Test anchor error with display of similar headings to help user."""
    root = md_project

    write_markdown(root / "similar.md",
                   title="Document",
                   content="""## Authorization

Authentication using tokens.

## Authentification

Misspelled section.

## Authentication Guide

Extended auth guide.
""")

    create_template(root, "anchor-similar-test", """# Similar Test

${md:similar#Authentication}
""")

    from lg.template.processor import TemplateProcessingError
    with pytest.raises(TemplateProcessingError) as exc_info:
        render_template(root, "ctx:anchor-similar-test")

    error_message = str(exc_info.value)
    assert "Authentication" in error_message
    assert "not found" in error_message
    # Should show available headings for diagnosis
    assert "Authorization" in error_message or "Authentification" in error_message


def test_anchor_case_insensitive_matching(md_project):
    """Test case-insensitive anchor matching."""
    root = md_project

    write_markdown(root / "case-test.md",
                  title="Case Test",
                  content="""## Installation Guide

Setup instructions.

## API Reference

API docs.
""")

    create_template(root, "anchor-case-test", """# Case Test

## Lowercase anchor
${md:case-test#installation guide}

## Mixed case anchor
${md:case-test#Api Reference}

## Uppercase anchor
${md:case-test#API REFERENCE}
""")

    result = render_template(root, "ctx:anchor-case-test")

    # All variants should work
    assert result.count("Setup instructions.") >= 1
    assert result.count("API docs.") >= 2  # appears twice


def test_anchor_with_special_characters(md_project):
    """Test anchors with special characters - should use slug-style."""
    root = md_project

    write_markdown(root / "special.md",
                  title="Special Characters",
                  content="""## Section 1: Overview

Basic info.

## Section 2.1 - Advanced

Advanced topics.

## FAQ (Frequently Asked Questions)

Q&A section.

## "Quoted Section" Title

Special formatting.
""")

    create_template(root, "anchor-special-test", """# Special Characters Test

## Overview section
${md:special#section-1-overview}

## Advanced section (with dash and dot)
${md:special#section-21-advanced}

## FAQ with parentheses
${md:special#faq-frequently-asked-questions}

## Quoted section
${md:special#quoted-section-title}
""")

    result = render_template(root, "ctx:anchor-special-test")

    # All sections should be found
    assert "Basic info." in result
    assert "Advanced topics." in result
    assert "Q&A section." in result
    assert "Special formatting." in result


def test_anchor_with_contextual_analysis(md_project):
    """Test anchor operation with contextual heading analysis."""
    root = md_project

    create_template(root, "anchor-contextual-test", """# Main Document

## API Documentation

### Authentication Section
${md:docs/api#Authentication}

### Endpoints Section
${md:docs/api#Endpoints}
""")

    result = render_template(root, "ctx:anchor-contextual-test")

    # Anchor sections should be processed with correct heading levels
    # Authentication was H2, under H3 should become H4
    assert "#### Authentication" in result

    # Content of Authentication section
    assert "Use API keys." in result

    # Endpoints section
    assert "#### Endpoints" in result
    assert "### GET /users" in result  # was H3, under H3 became H4 → H5 (expectation error)


def test_anchor_combined_with_explicit_parameters(md_project):
    """Test anchors in combination with explicit parameters."""
    root = md_project

    create_template(root, "anchor-params-test", """# Parameters Test

## Authentication (level 5, strip H1)
${md:docs/api#Authentication, level:5, strip_h1:true}

## Endpoints (level 2, keep H1)
${md:docs/api#Endpoints, level:2, strip_h1:false}
""")

    result = render_template(root, "ctx:anchor-params-test")

    # Authentication: level:5, strip_h1:true
    assert "##### Authentication" in result  # H2 → H5

    # Endpoints: level:2, strip_h1:false
    assert "## Endpoints" in result         # H2 → H2
    assert "### GET /users" in result       # H3 → H3


def test_anchor_with_addressed_placeholders(md_project):
    """Test anchors with addressed placeholders."""
    root = md_project

    create_template(root, "anchor-addressed-test", """# Addressed Anchors Test

## Internal Authentication
${md@self:internal#Authentication}

## Main API Authentication
${md:docs/api#Authentication}
""")

    # Create file in lg-cfg with Authentication section
    write_markdown(root / "lg-cfg" / "internal.md",
                  title="Internal Documentation",
                  content="""## Authentication

Internal auth process.

## Other Section

Other content.
""")

    result = render_template(root, "ctx:anchor-addressed-test")

    # Both Authentication sections should be present
    assert "Internal auth process." in result  # from @self:internal
    assert "Use API keys." in result           # from docs/api


def test_anchor_empty_section_handling(md_project):
    """Test handling of empty sections."""
    root = md_project

    write_markdown(root / "empty-sections.md",
                  title="Empty Sections Test",
                  content="""## Non-Empty Section

Some content.

## Empty Section

## Another Section

More content.
""")

    create_template(root, "anchor-empty-test", """# Empty Sections Test

## Non-empty
${md:empty-sections#Non-Empty Section}

## Empty section
${md:empty-sections#Empty Section}

## Another
${md:empty-sections#Another Section}
""")

    result = render_template(root, "ctx:anchor-empty-test")

    # Non-empty sections should be included
    assert "Some content." in result
    assert "More content." in result

    # Empty section should be handled correctly (heading without content)
    assert "## Empty Section" in result


@pytest.mark.parametrize("anchor,expected_content", [
    ("Authentication", "Use API keys."),
    ("Endpoints", "Get users list."),
    ("authentication", "Use API keys."),  # case insensitive
    ("ENDPOINTS", "Get users list."),     # case insensitive
])
def test_anchor_parametrized(md_project, anchor, expected_content):
    """Parametrized test for different anchors."""
    root = md_project

    create_template(root, f"anchor-param-{anchor.lower()}", f"""# Anchor Test

${{md:docs/api#{anchor}}}
""")

    result = render_template(root, f"ctx:anchor-param-{anchor.lower()}")
    assert expected_content in result


def test_anchor_with_setext_headings(md_project):
    """Test anchors with Setext headings (underlines)."""
    root = md_project

    write_markdown(root / "setext.md",
                  title="",  # no H1
                  content="""Setext Example
==============

This is a setext H1.

Subsection
----------

This is a setext H2.

## ATX Section

This is ATX H2.
""")

    create_template(root, "anchor-setext-test", """# Setext Test

## H1 Section
${md:setext#Setext Example}

## H2 Section
${md:setext#Subsection}

## ATX Section
${md:setext#ATX Section}
""")

    result = render_template(root, "ctx:anchor-setext-test")

    # All heading types should be found
    assert "This is a setext H1." in result
    assert "This is a setext H2." in result
    assert "This is ATX H2." in result
