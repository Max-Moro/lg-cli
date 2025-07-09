import pytest

from lg.adapters.markdown import MarkdownAdapter, LangMarkdown

@pytest.fixture
def adapter():
    return MarkdownAdapter()

def test_no_max_heading_level_leaves_text(adapter):
    text = "# Title\n\nSome text\n"
    cfg = LangMarkdown(max_heading_level=None)
    # без normalization текст не меняется
    assert adapter.process(text, cfg) == text

def test_remove_top_level_header(adapter):
    # single-file: убираем единственный top-level header
    text = "# My Document\n"
    cfg = LangMarkdown(max_heading_level=3)
    # после удаления остаётся пустая строка
    assert adapter.process(text, cfg) == ""

def test_shift_down_when_min_level_lt_max(adapter):
    # пример: заголовки ## и ###, max_heading_level=4 → shift=4-2=2
    text = "## Subtitle\n### SubSub\nParagraph\n"
    cfg = LangMarkdown(max_heading_level=4)
    out = adapter.process(text, cfg).splitlines()
    # теперь levels должны стать 4 и 5
    assert out[0].startswith("#### "), out[0]
    assert out[1].startswith("##### "), out[1]
    assert out[2] == "Paragraph"

def test_shift_up_when_min_level_gt_max(adapter):
    # пример: заголовки ### и ####, max_heading_level=2 → shift=2-3=-1
    text = "### Level3\n#### Level4\n"
    cfg = LangMarkdown(max_heading_level=2)
    out = adapter.process(text, cfg).splitlines()
    # ### → ##, #### → ###
    assert out[0].startswith("## "), out[0]
    assert out[1].startswith("### "), out[1]

def test_remove_and_shift_combined(adapter):
    # сначала удаляем # Title, потом shift
    text = "# Title\n## A\n### B\n"
    cfg = LangMarkdown(max_heading_level=3)
    out = adapter.process(text, cfg).splitlines()
    # после удаления first line, levels=[2,3], min_lvl=2, shift=3-2=1
    assert out[0].startswith("### A"), out[0]
    assert out[1].startswith("#### B"), out[1]

def test_preserve_non_header_lines(adapter):
    # строки без # не трогаем
    text = "# Title\nNo heading here\n## Sub\nPlain\n"
    cfg = LangMarkdown(max_heading_level=2)
    out = adapter.process(text, cfg).splitlines()
    # первая строка удалена
    assert out[0] == "No heading here"
    # Subshift: levels=[2], min_lvl=2, shift=0
    assert out[1].startswith("## Sub")
    assert out[2] == "Plain"
