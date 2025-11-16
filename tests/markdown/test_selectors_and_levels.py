import re

from tests.infrastructure import lctx_md
from .conftest import adapter

MD = """\
# Guide

## Getting Started
Intro

## CLI Options
--foo
--bar

## FAQ
### User
Q/A

### Dev
Q/A

## Legacy Notes
old
"""

def test_sections_match_by_slug():
    cfg = {
        "drop": {
            "sections": [
                {"match": {"kind": "slug", "pattern": "cli-options"}}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(drop {title} L{level}; {lines})*"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=MD))
    # Heading "## CLI Options" is absent
    assert re.search(r"^##\s+CLI Options\b", out, flags=re.M) is None
    # Placeholder with section name is present
    assert "> *(drop CLI Options L2; 4)*" in out
    # Other sections remained
    assert "## Getting Started" in out
    assert "## FAQ" in out
    # At least one placeholder was applied
    assert int(meta.get('md.placeholders', 0)) >= 1

def test_sections_match_by_regex_flags():
    cfg = {
        "drop": {
            "sections": [
                {"match": {"kind": "regex", "pattern": "^legacy", "flags": "i"}}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omitted {title})*"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=MD))
    # section heading (## Legacy Notes) is absent
    assert re.search(r"^##\s+Legacy Notes\b", out, flags=re.M) is None
    # but placeholder with title is inserted
    assert "> *(omitted Legacy Notes)*" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_sections_match_by_path_only():
    cfg = {
        "drop": {
            "sections": [
                {"path": ["FAQ", "User"], "placeholder": "> *(FAQ user pruned)*"}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(GEN)*"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=MD))
    assert "### User" not in out
    assert "### Dev" in out
    assert "> *(FAQ user pruned)*" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_sections_level_bounds():
    cfg = {
        "drop": {
            "sections": [
                # Remove only H2 sections (level_exact)
                {"match": {"kind": "regex", "pattern": "."}, "level_exact": 2, "reason": "demo"}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omit L{level} {title})*"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=MD))
    # All H2 sections (Getting Started, CLI Options, FAQ, Legacy Notes) removed completely
    assert "## " not in out
    # only root H1 remained
    assert "# Guide" in out
    # placeholders are present
    assert int(meta.get("md.placeholders", 0)) >= 1

def test_sections_match_plus_path_combo():
    cfg = {
        "drop": {
            "sections": [
                # Match by text + ancestor restriction (won't match because "Dev" ancestor is FAQ)
                {"match": {"kind": "text", "pattern": "Dev"}, "path": ["User"]},
                # Match by text + correct path
                {"match": {"kind": "text", "pattern": "Dev"}, "path": ["FAQ"]},
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=MD))
    assert "### Dev" not in out
    assert "### User" in out
    assert int(meta.get("md.placeholders", 0)) == 1
