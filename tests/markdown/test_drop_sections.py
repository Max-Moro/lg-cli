from tests.conftest import lctx_md
from .conftest import adapter

def test_drop_section_by_text_with_placeholder():
    text = """\
# Title

## Installation
step 1
step 2

## Keep
ok
"""
    cfg = {
        "drop": {
            "sections": [
                {
                    "match": {"kind": "text", "pattern": "Installation"},
                    "placeholder": "> *(Install removed; {lines} lines)*"
                }
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(Omitted {title}; −{lines} lines)*"},
        },
        "max_heading_level": 2,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    # Раздел Installation должен исчезнуть и появиться placeholder
    assert "Installation" not in out
    assert "step 1" not in out
    assert "step 2" not in out
    assert "Omitted" in out or "Install removed" in out
    # Keep остался
    assert "## Keep" in out
    assert int(meta.get("md.placeholders", 0)) >= 1



def test_frontmatter_removed_no_placeholder_when_none_mode():
    text = """\
---
title: Doc
---

# H1
"""
    cfg = {
        "drop": {
            "sections": [],
            "frontmatter": True,
            "placeholder": {"mode": "none"},
        },
        "max_heading_level": None,
    }
    out, meta = adapter(cfg).process(lctx_md(raw_text=text))
    # frontmatter исчез
    assert out.startswith("# H1")
    assert meta.get("md.removed.frontmatter") is True


