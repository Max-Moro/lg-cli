import pytest

from tree_sitter import Language

from lg.adapters.tree_sitter_support import TreeSitterDocument


class PyDoc(TreeSitterDocument):
    """Minimal concrete TreeSitterDocument for Python used in tests."""

    def get_language(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())

    def get_query_definitions(self) -> dict[str, str]:
        # Lightweight queries sufficient for behavior testing
        return {
            # Capture every identifier occurrence
            "ids": "(identifier) @id",
            # Basic function structure
            "funcs": (
                "(function_definition\n"
                "  name: (identifier) @fname\n"
                "  body: (block) @fbody) @fdef\n"
            ),
            # Strings for unicode/range testing
            "strings": "(string) @string",
        }


def test_query_unknown_and_query_opt():
    src = "def f():\n    return 1\n"
    doc = PyDoc(src, ext="py")

    # query() must raise on unknown name
    with pytest.raises(ValueError):
        doc.query("unknown_query_name")

    # query_opt() returns [] instead of raising
    assert doc.query_opt("unknown_query_name") == []


def test_query_cache_by_name_and_stable_results_order():
    src = """
def a():
    x = 1
    y = 2
def b():
    z = 3
"""
    doc = PyDoc(src, ext="py")

    # Initial call populates cache
    ids_1 = doc.query("ids")
    assert "ids" in doc._query_cache  # internal cache
    q1 = doc._query_cache["ids"]

    # Subsequent calls reuse same Query object
    ids_2 = doc.query("ids")
    q2 = doc._query_cache["ids"]
    assert q1 is q2

    # Order of captures should be stable across calls
    seq1 = [(n.start_byte, cap) for n, cap in ids_1]
    seq2 = [(n.start_byte, cap) for n, cap in ids_2]
    assert seq1 == seq2

    # A new document with same text should also produce the same order
    doc2 = PyDoc(src, ext="py")
    ids_3 = doc2.query("ids")
    seq3 = [(n.start_byte, cap) for n, cap in ids_3]
    assert seq1 == seq3


def test_get_node_text_and_ranges_with_unicode():
    # Include multibyte characters (Cyrillic + emoji)
    src = "# заголовок\nmsg = \"привет 🍕\"\n"
    doc = PyDoc(src, ext="py")

    strings = doc.query("strings")
    assert strings, "expected to capture a string literal"
    node, cap = strings[0]
    # Ranges returned by helper equal to Node offsets
    start, end = doc.get_node_range(node)
    assert start == node.start_byte and end == node.end_byte

    # Line range consistent with Node points
    lstart, lend = doc.get_line_range(node)
    assert lstart == node.start_point[0]
    assert lend == node.end_point[0]

    # Extracted text matches the source slice
    text = doc.get_node_text(node)
    # Decode slice from original to compare precisely
    raw_slice = src.encode("utf-8")[start:end].decode("utf-8")
    assert text == raw_slice
    assert "привет" in text and "🍕" in text


def test_get_line_number_for_byte_with_multibyte_chars():
    # Two lines; second contains multibyte characters
    src = "line1\nстрока2 🍕\n"
    doc = PyDoc(src, ext="py")

    b = src.encode("utf-8")
    # Byte offset right after the newline
    newline_pos = b.find(b"\n") + 1
    assert doc.get_line_number_for_byte(newline_pos) == 1

    # Offset in the middle of the unicode line still should be line 1 (0-based)
    # Pick a byte offset within the Cyrillic word
    off = newline_pos + 4  # not necessarily char-aligned, but within the line
    assert doc.get_line_number_for_byte(off) == 1


def test_errors_detection_valid_and_invalid_sources():
    valid = "def ok():\n    return 42\n"
    invalid = "def broken(:\n  pass\n"  # syntax error

    doc_ok = PyDoc(valid, ext="py")
    assert not doc_ok.has_error()
    assert doc_ok.get_errors() == []

    doc_bad = PyDoc(invalid, ext="py")
    # Tree-sitter for invalid code should flag errors
    assert doc_bad.has_error()
    errs = doc_bad.get_errors()
    assert isinstance(errs, list) and all(getattr(n, "type", None) == "ERROR" for n in errs)


def test_walk_and_find_nodes_by_type():
    src = """
def foo():
    return 1

def bar():
    return 2
"""
    doc = PyDoc(src, ext="py")

    # Basic walk should include the root node and many descendants
    walked = list(doc.walk_tree())
    assert walked, "walk_tree should yield nodes"
    # Root type for Python is typically 'module'
    assert getattr(walked[0], "type", None) in ("module", "program")

    # find_nodes_by_type should find both function definitions
    fdefs = doc.find_nodes_by_type("function_definition")
    assert len(fdefs) >= 2
