from tests.infrastructure import lctx_md
from .conftest import adapter

def test_keep_section_by_text():
    """Test preserving a single section by exact name match."""
    text = """\
# Title

## Installation
step 1
step 2

## Usage
usage info

## Advanced
advanced info
"""
    cfg = {
        "keep": {
            "sections": [
                {
                    "match": {"kind": "text", "pattern": "Usage"},
                    "reason": "Only keep usage section"
                }
            ],
            "frontmatter": False,
        },
        "max_heading_level": 2,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Only the Usage section should remain
    assert "## Usage" in out
    assert "usage info" in out
    
    # Other sections should be removed
    assert "## Installation" not in out
    assert "step 1" not in out
    assert "## Advanced" not in out
    
    # Verify mode was correctly identified
    assert meta.get("md.mode") == "keep"
    assert int(meta.get("md.removed.sections", 0)) > 0


def test_keep_multiple_sections():
    """Test preserving multiple sections."""
    text = """\
# Title

## Section A
content A

## Section B
content B

## Section C
content C
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "text", "pattern": "Section A"}},
                {"match": {"kind": "text", "pattern": "Section C"}}
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Sections A and C should be kept
    assert "## Section A" in out
    assert "content A" in out
    assert "## Section C" in out
    assert "content C" in out
    
    # Section B should be removed
    assert "## Section B" not in out
    assert "content B" not in out
    
    # Verify mode
    assert meta.get("md.mode") == "keep"


def test_keep_frontmatter():
    """Test preserving frontmatter when deleting all sections."""
    text = """\
---
title: Doc
tags: ["test"]
---

# Content
text content
"""
    cfg = {
        "keep": {
            "sections": [],  # No sections to keep
            "frontmatter": True
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Frontmatter should be preserved
    assert "---" in out
    assert "title: Doc" in out
    assert 'tags: ["test"]' in out
    
    # Content should be removed (since we're not keeping any sections)
    assert "# Content" not in out
    assert "text content" not in out
    
    # Verify mode
    assert meta.get("md.mode") == "keep"


def test_keep_section_by_slug():
    """Test keep mode using slug matching."""
    text = """\
# Main Title

## CLI Options & Flags
details about CLI

## User Guide
user instructions

## API Reference
api docs
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "slug", "pattern": "cli-options-flags"}},
                {"match": {"kind": "slug", "pattern": "api-reference"}}
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # CLI Options and API Reference should remain
    assert "## CLI Options & Flags" in out
    assert "details about CLI" in out
    assert "## API Reference" in out
    assert "api docs" in out
    
    # User Guide should be removed
    assert "## User Guide" not in out
    assert "user instructions" not in out


def test_keep_section_by_regex():
    """Test keep mode using regular expressions."""
    text = """\
# Documentation

## Getting Started
intro content

## Advanced Configuration
advanced stuff

## Advanced Topics
advanced topics

## Basic Usage
basic usage
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "regex", "pattern": "^Advanced", "flags": "i"}}
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Both Advanced sections should remain
    assert "## Advanced Configuration" in out
    assert "advanced stuff" in out
    assert "## Advanced Topics" in out
    assert "advanced topics" in out
    
    # Other sections should be removed
    assert "## Getting Started" not in out
    assert "## Basic Usage" not in out


def test_keep_with_level_constraints():
    """Test keep mode with heading level constraints."""
    text = """\
# Main

## Section A
content A

### Subsection A.1
subcontent A.1

## Section B
content B

### Subsection B.1
subcontent B.1
"""
    cfg = {
        "keep": {
            "sections": [
                {
                    "match": {"kind": "regex", "pattern": "Section"},
                    "level_exact": 2  # Only H2 level sections
                }
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # H2 sections should remain WITH their subsections (this is expected behavior)
    # because when we keep a section, we keep its entire subtree
    assert "## Section A" in out
    assert "content A" in out
    assert "## Section B" in out 
    assert "content B" in out
    
    # H3 subsections are part of their parent sections, so they stay too
    assert "### Subsection A.1" in out
    assert "### Subsection B.1" in out
    
    # Only the main title should be removed
    assert "# Main" not in out


def test_keep_no_sections_found():
    """Test keep mode when no sections are found - all content should be removed."""
    text = """\
# Title

## Installation
install instructions

## Usage
usage instructions
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "text", "pattern": "NonexistentSection"}}
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Nothing should remain since no sections matched
    assert "## Installation" not in out
    assert "## Usage" not in out
    assert "install instructions" not in out
    assert "usage instructions" not in out
    
    # Should contain only file label
    assert out.strip() == "<!-- FILE: test.md -->"


def test_keep_and_drop_mutual_exclusion():
    """Test that keep and drop modes are mutually exclusive."""
    try:
        cfg = {
            "keep": {
                "sections": [{"match": {"kind": "text", "pattern": "Usage"}}]
            },
            "drop": {
                "sections": [{"match": {"kind": "text", "pattern": "Installation"}}]
            }
        }
        adapter(cfg)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Cannot use both 'drop' and 'keep' modes simultaneously" in str(e)


def test_keep_with_frontmatter_and_sections():
    """Test keep mode with both frontmatter and specific sections preserved."""
    text = """\
---
title: Documentation
version: 1.0
---

# Main Title

## Important Section
important content

## Unimportant Section
unimportant content
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "text", "pattern": "Important Section"}}
            ],
            "frontmatter": True
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # Frontmatter should be preserved
    assert "---" in out
    assert "title: Documentation" in out
    assert "version: 1.0" in out
    
    # Important section should be preserved
    assert "## Important Section" in out
    assert "important content" in out
    
    # Unimportant section should be removed
    assert "## Unimportant Section" not in out
    assert "unimportant content" not in out


def test_keep_mode_no_placeholders():
    """Test that no placeholders are inserted in keep mode."""
    text = """\
# Title

## Keep This
keep content

## Remove This
remove content
"""
    cfg = {
        "keep": {
            "sections": [
                {"match": {"kind": "text", "pattern": "Keep This"}}
            ]
        }
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    
    # No placeholders should be inserted
    assert meta.get("md.placeholders", 0) == 0
    assert "*(omitted" not in out.lower()
    assert "*(Omitted" not in out
    
    # Only kept content should remain
    assert "## Keep This" in out
    assert "keep content" in out
    assert "## Remove This" not in out
    assert "remove content" not in out