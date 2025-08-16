import re
import pytest

from lg_vnext.adapters.markdown import MarkdownAdapter, MarkdownCfg

adapter = MarkdownAdapter()

@pytest.mark.parametrize("text, max_lvl, group_size, mixed, expected, expected_meta", [
    # 1) single-file + max_heading_level=3: убираем H1, сдвигаем H2→H3, H3→H4
    (
        "# Title\n## Subtitle\n### Subsubtitle",
        3, 1, False,
        "### Subtitle\n#### Subsubtitle",
        {"removed_h1": 1, "shifted": True},
    ),
    # 2) single-file + max_heading_level=2: убираем H1, H2→H2, H3→H3 (shift=0)
    (
        "# A\n## B\n### C",
        2, 1, False,
        "## B\n### C",
        {"removed_h1": 1, "shifted": True},
    ),
    # 3) group_size>1 — только сдвиг (min_lvl=1 → shift=2): H1→###, H2→####
    (
        "# X\n## Y\n",
        3, 2, False,
        "### X\n#### Y",
        {"removed_h1": 0, "shifted": True},
    ),
    # 4) mixed=True — не трогаем
    (
        "# MTitle\n## MSub\n",
        3, 1, True,
        "# MTitle\n## MSub\n",
        {"removed_h1": 0, "shifted": False},
    ),
    # 5) max_heading_level=None — не трогаем
    (
        "# Z\n## Q",
        None, 1, False,
        "# Z\n## Q",
        {"removed_h1": 0, "shifted": False},
    ),
    # 6) нет заголовков — возвращаем как есть
    (
        "Just some text\n- list item\n",
        2, 1, False,
        "Just some text\n- list item",
        {"removed_h1": 0, "shifted": False},
    ),
])
def test_header_normalization(text, max_lvl, group_size, mixed, expected, expected_meta):
    cfg = MarkdownCfg(max_heading_level=max_lvl)
    out, meta = adapter.process(text, cfg, group_size, mixed)
    # сравниваем линии напрямую
    assert out == expected
    # и метаданные тоже
    assert meta == expected_meta

def test_only_strips_single_h1_line_when_alone():
    # если только H1 и никаких подзаголовков – убираем его, получаем пустую строку
    text = "# Lone Title\n"
    cfg = MarkdownCfg(max_heading_level=3)
    out, meta = adapter.process(text, cfg, group_size=1, mixed=False)
    assert out == ""
    # В этом граничном кейсе min_lvl отсутствует → shifted остаётся False,
    # но removed_h1 обязательно должен быть 1.
    assert meta == {"removed_h1": 1, "shifted": False}

def test_complex_markdown_preserves_non_header_content():
    text = "# T\n## A\nPara line\n### B\n- item\n"
    cfg = MarkdownCfg(max_heading_level=2)
    # group_size=1 → удаляет # T, shift = 2-2 = 0
    out, meta = adapter.process(text, cfg, group_size=1, mixed=False)
    lines = out.splitlines()
    # первая строка должна быть "## A"
    assert lines[0] == "## A"
    # следующая — "Para line"
    assert "Para line" in lines
    # а потом "### B"
    assert any(re.match(r"^###\s+B", ln) for ln in lines)
    # метаданные: H1 снят, сдвига нет (но shifted True, т.к. флаг трактуется как «была нормализация»)
    assert meta == {"removed_h1": 1, "shifted": True}

def test_code_block_comments_not_counted_as_headings():
    # В Markdown-статье есть H1, затем fenced-код с комментарием,
    # а после — подзаголовок.
    text = """\
# Article Title

Some intro text.

```python
# this is a code comment
print("hello")
````

## Next Section

"""
    # Убираем H1, max_heading_level=2 → Next Section остаётся на уровне 2,
    # а комментарий в коде не трогаем
    cfg = MarkdownCfg(max_heading_level=2)
    out, meta = adapter.process(text, cfg, group_size=1, mixed=False)
    lines = out.splitlines()


    # H1 удалён
    assert not any(ln.startswith("# Article Title") for ln in lines)
    # Комментарий в коде не превращается в H2 или удаляется
    assert "# this is a code comment" in lines, "code comment was mangled"
    # Следующий заголовок остаётся именно "## Next Section"
    assert any(ln == "## Next Section" for ln in lines)
    # метаданные: H1 снят; сдвиг уровней = 0, но считаем «нормализация была»
    assert meta == {"removed_h1": 1, "shifted": True}


