from lg.markdown.parser import parse_markdown

def test_parse_atx_and_setext_and_fenced():
    text = """\
# Title H1

Para

```python
# inside code
## not a heading
````

## Section

## Sub

"""
    doc = parse_markdown(text)
    # Headings: H1 "Title H1", Setext "Section" (H2), ATX "Sub" (H2)
    titles = [(h.level, h.title) for h in doc.headings]
    assert titles == [(1, "Title H1"), (2, "Section"), (2, "Sub")]


    # Subtrees: H1 → until "Section"; "Section" → until "## Sub"; "Sub" → to end
    # Verify that boundaries are reasonable and monotonic
    assert doc.headings[0].start_line == 0
    assert doc.headings[0].end_line_excl > doc.headings[0].start_line
    assert doc.headings[1].start_line > doc.headings[0].start_line
    assert doc.headings[2].start_line > doc.headings[1].start_line


def test_frontmatter_detection():
    text = """\
------------

title: Doc
tags:

* a

---

# H1

"""
    doc = parse_markdown(text)
    # Parser returns the FULL frontmatter range (including both delimiters and trailing empty lines)
    assert doc.frontmatter_range == (0, 9)
    # Verify that H1 is still parsed correctly
    assert [(h.level, h.title) for h in doc.headings] == [(1, "H1")]