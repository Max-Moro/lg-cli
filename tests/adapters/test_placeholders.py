import pytest

from lg.adapters.placeholders import create_placeholder_manager, PlaceholderSpec


def make_manager(text: str, style: str = "inline"):
    """Helper: create a PlaceholderManager with Python-like comment style.

    single: '#', block: '/* */', docstring: '""" """'
    """
    return create_placeholder_manager(
        raw_text=text,
        comment_style_tuple=("#", ("/*", "*/"), ('"""', '"""')),
        placeholder_style=style,
    )


def line_of(text: str, byte_pos: int) -> int:
    return text[:byte_pos].count("\n")


def test_generate_inline_block_and_docstring_placeholders():
    text = "def foo():\n    pass\n\n\n"

    # Inline style
    pm_inline = make_manager(text, style="inline")
    # Span covers two lines (function body)
    start = text.find(":") + 1
    end = text.find("\n\n")
    pm_inline.add_placeholder(
        placeholder_type="function_body",
        start_char=start,
        end_char=end,
        start_line=line_of(text, start),
        end_line=line_of(text, end),
    )
    edits_inline, stats_inline = pm_inline.finalize_edits()
    assert len(edits_inline) == 1
    spec, repl = edits_inline[0]
    # Inline uses '# '
    assert repl.startswith("# ")
    assert "function body omitted" in repl
    # 2 lines (body plus newline) captured in placeholder content suffix
    assert "lines" in repl
    assert stats_inline["placeholders_inserted"] == 1

    # Block style
    pm_block = make_manager(text, style="block")
    pm_block.add_placeholder(
        placeholder_type="function_body",
        start_char=start,
        end_char=end,
        start_line=line_of(text, start),
        end_line=line_of(text, end),
    )
    edits_block, _ = pm_block.finalize_edits()
    spec_b, repl_b = edits_block[0]
    assert repl_b.startswith("/* ") and repl_b.endswith(" */")
    assert "function body omitted" in repl_b

    # Docstring placeholder always uses docstring delimiters
    pm_doc = make_manager(text, style="inline")
    pm_doc.add_placeholder(
        placeholder_type="docstring",
        start_char=0,
        end_char=0,
        start_line=0,
        end_line=0,
    )
    edits_doc, _ = pm_doc.finalize_edits()
    _, repl_d = edits_doc[0]
    assert repl_d.startswith('""" ')
    assert repl_d.endswith(' """')
    assert "docstring omitted" in repl_d


def test_collapse_same_type_with_only_whitespace_between():
    # Two imports separated by blank lines -> should collapse
    text = "import a\n\n\nimport b\n"
    pm = make_manager(text)

    # First placeholder at beginning
    start1 = 0
    end1 = text.find("\n\n\n")
    pm.add_placeholder(
        placeholder_type="import",
        start_char=start1,
        end_char=end1,
        start_line=line_of(text, start1),
        end_line=line_of(text, end1),
        count=1,
    )

    # Second placeholder after blank lines
    start2 = end1 + 3  # skip the three newlines
    end2 = len(text)
    pm.add_placeholder(
        placeholder_type="import",
        start_char=start2,
        end_char=end2,
        start_line=line_of(text, start2),
        end_line=line_of(text, end2),
        count=1,
    )

    edits, stats = pm.finalize_edits()
    # Collapsed into single placeholder
    assert len(edits) == 1
    spec, repl = edits[0]
    # Count should be aggregated (2 imports)
    assert spec.count == 2
    assert "2 imports omitted" in repl
    assert stats["placeholders_inserted"] == 1
    assert stats["placeholders_by_type"]["import"] == 2


def test_no_collapse_when_code_between():
    # Placeholders separated by non-whitespace code must not collapse
    text = "from x import y\nprint(y)\nfrom a import b\n"
    pm = make_manager(text)

    # First import statement
    start1 = 0
    end1 = text.find("\n") + 1
    pm.add_placeholder(
        placeholder_type="import",
        start_char=start1,
        end_char=end1,
        start_line=line_of(text, start1),
        end_line=line_of(text, end1),
    )

    # Second import statement after a code line
    start2 = text.rfind("from")
    end2 = len(text)
    pm.add_placeholder(
        placeholder_type="import",
        start_char=start2,
        end_char=end2,
        start_line=line_of(text, start2),
        end_line=line_of(text, end2),
    )

    edits, stats = pm.finalize_edits()
    assert len(edits) == 2
    # Ensure each replacement corresponds to a single import
    assert all("import omitted" in r for _, r in edits)


def test_different_indentation_blocks_collapse():
    # Same type with different column positions should not collapse
    text = "import a\n    import b\n"
    pm = make_manager(text)

    # First starts at column 0
    start1 = 0
    end1 = text.find("\n")
    pm.add_placeholder("import", start1, end1, 0, 0)

    # Second starts after 4 spaces
    # Use first non-space char to reflect actual column (4)
    nl_pos = text.find("\n")
    line2 = text[nl_pos + 1:]
    # index of first non-space in line2
    first_non_space = len(line2) - len(line2.lstrip(" "))
    start2 = nl_pos + 1 + first_non_space
    end2 = len(text) - 1
    pm.add_placeholder("import", start2, end2, 1, 1)

    edits, _ = pm.finalize_edits()
    assert len(edits) == 2


def test_style_none_produces_empty_replacements_but_keeps_stats():
    text = "x = 1\n"
    pm = make_manager(text, style="none")
    pm.add_placeholder("import", 0, 0, 0, 0)
    pm.add_placeholder("import", 0, 0, 0, 0)
    edits, stats = pm.finalize_edits()
    # Collapses because identical positions and whitespace-only between
    assert len(edits) == 1
    _, repl = edits[0]
    assert repl == ""  # style none → empty replacement
    assert stats["placeholders_inserted"] == 1
    assert stats["placeholders_by_type"]["import"] == 2


def test_placeholder_prefix_is_preserved():
    text = "line\n"
    pm = make_manager(text, style="inline")
    pm.add_placeholder(
        placeholder_type="import",
        start_char=0,
        end_char=0,
        start_line=0,
        end_line=0,
        placeholder_prefix="    ",
        count=3,
    )
    edits, _ = pm.finalize_edits()
    _, repl = edits[0]
    assert repl.startswith("    # ")
    assert "3 imports omitted" in repl
