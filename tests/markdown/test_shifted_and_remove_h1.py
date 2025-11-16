import re

import pytest

from tests.infrastructure import lctx_md


# Helper: verify only expected fields without requiring exact match of all keys.
def assert_meta_subset(meta: dict, expected_subset: dict):
    for k, v in expected_subset.items():
        assert meta.get(k) == v, f"meta[{k!r}] = {meta.get(k)!r}, expected {v!r}"

def make_adapter(max_lvl, strip_h1):
    """
    New configuration method: via bind(raw_cfg).
    Pass raw dict; fields match MarkdownCfg dataclass.
    """
    from .conftest import adapter
    raw_cfg = {"max_heading_level": max_lvl, "strip_h1": strip_h1}
    return adapter(raw_cfg)

@pytest.mark.parametrize("text, max_lvl, strip_h1, group_size, expected, expected_meta", [
    # 1) single-file + max_heading_level=3: remove H1, shift H2→H3, H3→H4
    (
        "# Title\n## Subtitle\n### Subsubtitle",
        3, True, 1,
        "<!-- FILE: test.md -->\n### Subtitle\n#### Subsubtitle",
        {"md.removed_h1": 1, "md.shifted": True, "md.file_label_inserted": True},
    ),
    # 2) single-file + max_heading_level=2: remove H1, H2→H2, H3→H3 (shift=0)
    (
        "# A\n## B\n### C",
        2, True, 1,
        "<!-- FILE: test.md -->\n## B\n### C",
        {"md.removed_h1": 1, "md.shifted": False, "md.file_label_inserted": True},
    ),
    # 3) strip_h1=True always removes H1, then shift: ## Y → ### Y
    (
        "# X\n## Y\n",
        3, True, 2,
        "<!-- FILE: test.md -->\n### Y",
        {"md.removed_h1": 1, "md.shifted": True, "md.file_label_inserted": True},
    ),
    # 4) strip_h1=False — only shift (min_lvl=1 → shift=2): H1→###, H2→####
    (
        "# X\n## Y\n",
        3, False, 2,
        "### X\n<!-- FILE: test.md -->\n#### Y",
        {"md.removed_h1": 0, "md.shifted": True, "md.file_label_inserted": True},
    ),
    # 6) max_heading_level=None, strip_h1=False — no changes
    (
        "# Z\n## Q",
        None, False, 1,
        "# Z\n<!-- FILE: test.md -->\n## Q",
        {"md.removed_h1": 0, "md.shifted": False, "md.file_label_inserted": True},
    ),
    # 7) no headings — return as is
    (
        "Just some text\n- list item\n",
        2, True, 1,
        "<!-- FILE: test.md -->\nJust some text\n- list item",
        {"md.removed_h1": 0, "md.shifted": False, "md.file_label_inserted": True},
    ),
])
def test_header_normalization(text, max_lvl, strip_h1, group_size, expected, expected_meta):
    adapter = make_adapter(max_lvl, strip_h1)
    out, meta = adapter.process(lctx_md(text, group_size))
    # compare lines directly
    assert out == expected
    # and metadata too
    assert_meta_subset(meta, expected_meta)

def test_only_strips_single_h1_line_when_alone():
    # if only H1 and no subheadings – remove it, get file label
    text = "# Lone Title\n"
    adapter = make_adapter(3, True)
    out, meta = adapter.process(lctx_md(raw_text=text))
    assert out == "<!-- FILE: test.md -->"
    # In this edge case min_lvl is absent → shifted remains False,
    # but removed_h1 must be 1.
    assert_meta_subset(meta, {"md.removed_h1": 1, "md.shifted": False, "md.file_label_inserted": True})

def test_complex_markdown_preserves_non_header_content():
    text = "# T\n## A\nPara line\n### B\n- item\n"
    adapter = make_adapter(2, True)
    # strip_h1=True → removes # T, shift = 2-2 = 0
    out, meta = adapter.process(lctx_md(raw_text=text))
    lines = out.splitlines()
    # first line should be file label
    assert lines[0] == "<!-- FILE: test.md -->"
    # second line should be "## A"
    assert lines[1] == "## A"
    # next is "Para line"
    assert "Para line" in lines
    # then "### B"
    assert any(re.match(r"^###\s+B", ln) for ln in lines)
    # metadata: H1 removed, no shift (but shifted True because flag means 'normalization occurred')
    assert_meta_subset(meta, {"md.removed_h1": 1, "md.shifted": False, "md.file_label_inserted": True})

def test_code_block_comments_not_counted_as_headings():
    # Markdown article has H1, then fenced code with comment,
    # then a subheading.
    text = """\
# Article Title

Some intro text.

```python
# this is a code comment
print("hello")
````

## Next Section

"""
    # Remove H1, max_heading_level=2 → Next Section stays at level 2,
    # code comment is not touched
    adapter = make_adapter(2, True)
    out, meta = adapter.process(lctx_md(raw_text=text))
    lines = out.splitlines()


    # H1 removed
    assert not any(ln.startswith("# Article Title") for ln in lines)
    # Code comment is not converted to H2 or deleted
    assert "# this is a code comment" in lines, "code comment was mangled"
    # Next heading stays as "## Next Section"
    assert any(ln == "## Next Section" for ln in lines)
    # metadata: H1 removed; level shift = 0, but consider 'normalization occurred'
    assert_meta_subset(meta, {"md.removed_h1": 1, "md.shifted": False})


