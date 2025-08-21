from lg.adapters.markdown import MarkdownAdapter

def test_merge_section_over_marker_prefers_section_placeholder():
    text = """\
# T

## Installation
<!-- lg:omit:start -->
minor note
<!-- lg:omit:end -->
steps
## Keep
ok
"""
    cfg = {
        "drop": {
            "sections": [
                {"match": {"kind": "text", "pattern": "Installation"}, "placeholder": "> *(SECTION)*"}
            ],
            "markers": [
                {"start": "<!-- lg:omit:start -->", "end": "<!-- lg:omit:end -->", "include_markers": True}
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(GEN)*"},
        },
        "max_heading_level": None,
    }
    out, meta = MarkdownAdapter().bind(cfg).process(text, group_size=1, mixed=False)  # type: ignore
    # Должен быть ОДИН placeholder и именно секционного шаблона
    assert out.count("SECTION") == 1
    assert out.count("GEN") == 0
    assert int(meta.get("md.placeholders", 0)) == 1
    assert "## Keep" in out
    assert "ok" in out


def test_merge_adjacent_markers_collapse_to_one_placeholder():
    text = """\
# T

<!-- a:start -->
block A
<!-- a:end -->
<!-- b:start -->
block B
<!-- b:end -->

end
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- a:start -->", "end": "<!-- a:end -->", "include_markers": True},
                {"start": "<!-- b:start -->", "end": "<!-- b:end -->", "include_markers": True},
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    out, meta = MarkdownAdapter().bind(cfg).process(text, group_size=1, mixed=False)  # type: ignore
    assert out.count("*(PH)*") == 1
    assert "end" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_placeholder_surrounded_by_single_blank_line():
    text = """\
# T


<!-- lg:omit:start -->
A
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
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    out, _ = MarkdownAdapter().bind(cfg).process(text, group_size=1, mixed=False)  # type: ignore
    # Не должно быть тройных пустых строк
    assert "\n\n\n" not in out
    # Разумный шов: максимум двойные переводы
    assert "> *(PH)*" in out


def test_no_triple_blank_lines_after_transform():
    text = """\
# T


<!-- s -->
A
<!-- e -->


<!-- s -->
B
<!-- e -->


tail
"""
    cfg = {
        "drop": {
            "sections": [],
            "markers": [
                {"start": "<!-- s -->", "end": "<!-- e -->", "include_markers": True},
                {"start": "<!-- s -->", "end": "<!-- e -->", "include_markers": True},
            ],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    out, _ = MarkdownAdapter().bind(cfg).process(text, group_size=1, mixed=False)  # type: ignore
    assert "\n\n\n" not in out
