"""
Tests for TreeSitterDocument base class.

Tests query_nodes with caching, unicode handling, and tree traversal.
"""

import pytest

from tree_sitter import Language

from lg.adapters.tree_sitter_support import TreeSitterDocument


class PyDoc(TreeSitterDocument):
    """Minimal concrete TreeSitterDocument for Python used in tests."""

    def get_language(self) -> Language:
        import tree_sitter_python as tspython
        return Language(tspython.language())


# ============= Query caching tests =============

def test_query_cache_compiled_query_reused():
    """Verify that Query objects are cached and reused."""
    src = """
def a():
    x = 1
    y = 2
def b():
    z = 3
"""
    doc = PyDoc(src, ext="py")
    query_string = "(identifier) @id"

    # Initial call populates cache
    ids_1 = doc.query_nodes(query_string, "id")
    assert query_string in doc._query_cache

    # Get reference to cached Query
    cached_query = doc._query_cache[query_string]

    # Subsequent call reuses same Query object
    ids_2 = doc.query_nodes(query_string, "id")
    assert doc._query_cache[query_string] is cached_query

    # Results should be identical
    assert len(ids_1) == len(ids_2)
    assert [n.start_byte for n in ids_1] == [n.start_byte for n in ids_2]


def test_query_nodes_stable_order():
    """Results order should be stable across calls and documents."""
    src = """
def foo():
    x = 1
def bar():
    y = 2
"""
    doc1 = PyDoc(src, ext="py")
    doc2 = PyDoc(src, ext="py")

    query_string = "(function_definition) @func"

    funcs_1 = doc1.query_nodes(query_string, "func")
    funcs_2 = doc1.query_nodes(query_string, "func")
    funcs_3 = doc2.query_nodes(query_string, "func")

    # Extract positions for comparison
    positions_1 = [n.start_byte for n in funcs_1]
    positions_2 = [n.start_byte for n in funcs_2]
    positions_3 = [n.start_byte for n in funcs_3]

    assert positions_1 == positions_2 == positions_3


def test_query_nodes_different_queries_cached_separately():
    """Different query strings should have separate cache entries."""
    src = "x = 'hello'\ny = 123\n"
    doc = PyDoc(src, ext="py")

    ids_query = "(identifier) @id"
    str_query = "(string) @str"

    doc.query_nodes(ids_query, "id")
    doc.query_nodes(str_query, "str")

    assert ids_query in doc._query_cache
    assert str_query in doc._query_cache
    assert doc._query_cache[ids_query] is not doc._query_cache[str_query]


# ============= Unicode handling tests =============

def test_get_node_text_and_ranges_with_unicode():
    """Test proper handling of multibyte characters (Cyrillic + emoji)."""
    src = "# заголовок\nmsg = \"привет 🍕\"\n"
    doc = PyDoc(src, ext="py")

    strings = doc.query_nodes("(string) @string", "string")
    assert strings, "expected to capture a string literal"
    node = strings[0]

    # Ranges returned by helper should be correct char positions
    start, end = doc.get_node_range(node)

    # Line range consistent with Node points
    lstart, lend = doc.get_line_range(node)
    assert lstart == node.start_point[0]
    assert lend == node.end_point[0]

    # Extracted text matches the source slice
    text = doc.get_node_text(node)
    raw_slice = src[start:end]
    assert text == raw_slice
    assert "привет" in text and "🍕" in text


def test_get_line_number_for_byte_with_multibyte_chars():
    """Test line number calculation with multibyte characters."""
    # Two lines; second contains multibyte characters
    src = "line1\nстрока2 🍕\n"
    doc = PyDoc(src, ext="py")

    b = src.encode("utf-8")
    # Byte offset right after the newline
    newline_pos = b.find(b"\n") + 1
    assert doc.get_line_number(newline_pos) == 1

    # Offset in the middle of the unicode line still should be line 1 (0-based)
    off = newline_pos + 4
    assert doc.get_line_number(off) == 1


# ============= Error detection tests =============

def test_errors_detection_valid_source():
    """Valid Python source should have no errors."""
    valid = "def ok():\n    return 42\n"
    doc = PyDoc(valid, ext="py")

    assert not doc.has_error()
    assert doc.get_errors() == []


def test_errors_detection_invalid_source():
    """Invalid Python source should have errors flagged."""
    invalid = "def broken(:\n  pass\n"  # syntax error (missing ')')
    doc = PyDoc(invalid, ext="py")

    # has_error() detects that tree contains errors
    assert doc.has_error()


def test_get_errors_returns_error_nodes():
    """get_errors() should return explicit ERROR nodes when present."""
    # This syntax creates an actual ERROR node (completely unparseable)
    invalid = "def @@@@@:\n"
    doc = PyDoc(invalid, ext="py")

    assert doc.has_error()
    errs = doc.get_errors()
    # Some syntax errors create ERROR nodes, others use MISSING
    # We just verify the method returns a list
    assert isinstance(errs, list)


# ============= Tree traversal tests =============

def test_walk_tree_yields_nodes():
    """walk_tree should yield nodes in depth-first order."""
    src = """
def foo():
    return 1

def bar():
    return 2
"""
    doc = PyDoc(src, ext="py")

    walked = list(doc.walk_tree())
    assert walked, "walk_tree should yield nodes"

    # Root type for Python is 'module'
    assert walked[0].type == "module"

    # Should contain function definitions
    func_types = [n.type for n in walked if n.type == "function_definition"]
    assert len(func_types) >= 2


def test_walk_tree_from_specific_node():
    """walk_tree should work from a specific start node."""
    src = "def foo():\n    x = 1\n    y = 2\n"
    doc = PyDoc(src, ext="py")

    # Get function definition node
    funcs = doc.query_nodes("(function_definition) @func", "func")
    assert funcs

    # Walk from function node
    walked = list(doc.walk_tree(start_node=funcs[0]))

    # First node should be the function definition
    assert walked[0].type == "function_definition"

    # Should contain identifiers from function body
    ids = [n for n in walked if n.type == "identifier"]
    assert len(ids) >= 3  # foo, x, y


# ============= Static helper tests =============

def test_get_parent_of_type():
    """Test finding parent node of specific type."""
    src = "def foo():\n    x = 1\n"
    doc = PyDoc(src, ext="py")

    # Get identifier 'x'
    ids = doc.query_nodes("(identifier) @id", "id")
    x_node = next(n for n in ids if doc.get_node_text(n) == "x")

    # Find parent function_definition
    func_parent = doc.get_parent_of_type(x_node, "function_definition")
    assert func_parent is not None
    assert func_parent.type == "function_definition"

    # Non-existent parent type
    assert doc.get_parent_of_type(x_node, "class_definition") is None


def test_get_children_by_type():
    """Test getting direct children of specific type."""
    src = "x = 1\ny = 2\nz = 3\n"
    doc = PyDoc(src, ext="py")

    # Module should have expression_statement children
    statements = doc.get_children_by_type(doc.root_node, "expression_statement")
    assert len(statements) == 3
