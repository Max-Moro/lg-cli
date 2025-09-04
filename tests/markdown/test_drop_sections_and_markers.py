from lg.adapters.markdown import MarkdownAdapter


from tests.conftest import lctx_md

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
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(Omitted {title}; −{lines} lines)*"},
        },
        "max_heading_level": 2,
    }
    adapter = MarkdownAdapter().bind(cfg)  # type: ignore
    out, meta = adapter.process(lctx_md(raw_text=text))
    # Раздел Installation должен исчезнуть и появиться placeholder
    assert "Installation" not in out
    assert "step 1" not in out
    assert "step 2" not in out
    assert "Omitted" in out or "Install removed" in out
    # Keep остался
    assert "## Keep" in out
    assert int(meta.get("md.placeholders", 0)) >= 1

def test_drop_by_markers_including_markers():
    text = """\
# Title

<!-- lg:omit:start -->
noise
<!-- lg:omit:end -->

Body
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- lg:omit:start -->", "end": "<!-- lg:omit:end -->", "include_markers": True}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omitted; {lines})*"},
        },
        "max_heading_level": None,
    }
    adapter = MarkdownAdapter().bind(cfg)  # type: ignore
    out, meta = adapter.process(lctx_md(raw_text=text))
    assert "noise" not in out
    assert "lg:omit" not in out
    assert "Body" in out
    assert int(meta.get("md.placeholders", 0)) == 1

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
            "markers": [],
            "frontmatter": True,
            "placeholder": {"mode": "none"},
        },
        "max_heading_level": None,
    }
    adapter = MarkdownAdapter().bind(cfg)  # type: ignore
    out, meta = adapter.process(lctx_md(raw_text=text))
    # frontmatter исчез
    assert out.startswith("# H1")
    assert meta.get("md.removed.frontmatter") is True

def test_marker_match_with_trailing_spaces():
    text = """\
# T

<!-- lg:omit:start   -->
noise
<!-- lg:omit:end -->
tail
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- lg:omit:start -->", "end": "<!-- lg:omit:end -->", "include_markers": True}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omitted; {lines})*"},
        },
        "max_heading_level": None,
    }
    from lg.adapters.markdown import MarkdownAdapter
    out, meta = MarkdownAdapter().bind(cfg).process(lctx_md(raw_text=text))  # type: ignore
    assert "noise" not in out
    assert "lg:omit" not in out
    assert "tail" in out
    assert int(meta.get("md.placeholders", 0)) == 1


def test_marker_match_with_indentation():
    text = """\
# T

    <!-- lg:omit:start -->
noise
    <!-- lg:omit:end -->

tail
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- lg:omit:start -->", "end": "<!-- lg:omit:end -->", "include_markers": True}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omitted; {lines})*"},
        },
        "max_heading_level": None,
    }
    from lg.adapters.markdown import MarkdownAdapter
    out, meta = MarkdownAdapter().bind(cfg).process(lctx_md(raw_text=text))  # type: ignore
    assert "noise" not in out
    assert "lg:omit" not in out
    assert "tail" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_marker_match_mixed_spaces_tabs():
    text = """\
# T
\t<!-- mark:start -->
noise
    <!-- mark:end -->
ok
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- mark:start -->", "end": "<!-- mark:end -->", "include_markers": True}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    from lg.adapters.markdown import MarkdownAdapter
    out, meta = MarkdownAdapter().bind(cfg).process(lctx_md(raw_text=text))  # type: ignore
    assert "noise" not in out
    assert int(meta.get("md.placeholders", 0)) == 1
    assert "ok" in out

def test_default_lg_omit_markers_work_without_drop():
    text = """\
# T

<!-- lg:omit:start -->
noise
<!-- lg:omit:end -->

ok
"""
    # Конфиг без drop: {}
    cfg = {"max_heading_level": None}
    out, meta = MarkdownAdapter().bind(cfg).process(lctx_md(raw_text=text))  # type: ignore
    assert "noise" not in out
    assert "lg:omit" not in out
    assert "ok" in out
