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
    # Заголовки: H1 "Title H1", Setext "Section" (H2), ATX "Sub" (H2)
    titles = [(h.level, h.title) for h in doc.headings]
    assert titles == [(1, "Title H1"), (2, "Section"), (2, "Sub")]


    # Поддеревья: H1 → до "Section"; "Section" → до "## Sub"; "Sub" → до конца
    # Проверим, что границы разумные и монотонные
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
    assert doc.frontmatter_range == (0, 6)  # 0..5 — frontmatter, end_excl=6
    # Проверим, что H1 всё равно парсится
    assert [(h.level, h.title) for h in doc.headings] == [(1, "H1")]