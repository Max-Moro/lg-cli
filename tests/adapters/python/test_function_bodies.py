"""
Tests for function body optimization in Python adapter.
"""

from lg.adapters.langs.python import PythonCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestPythonFunctionBodyOptimization:
    """Test function body stripping for Python code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("python.removed.function_body", 0) == 1
        assert meta.get("python.removed.method_body", 0) == 3
        assert "# … method body omitted" in result
        assert "# … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_max_tokens_trimming(self, do_function_bodies):
        """Test trimming function bodies to token budget."""
        adapter = make_adapter(PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="keep_all",
                max_tokens=20
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        # Bodies exceeding 20 tokens should be trimmed
        assert_golden_match(result, "function_bodies", "max_tokens_trim")

    def test_no_stripping(self, do_function_bodies):
        """Test with stripping disabled."""
        adapter = make_adapter(PythonCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("python.removed.function_body", 0) == 0
        assert meta.get("python.removed.method_body", 0) == 0
        assert "def add(self, a: int, b: int) -> int:" in result
        assert "result = a + b" in result

    def test_keep_public_policy(self):
        """Test keep_public policy - strips private, keeps public."""
        code = '''def public_function():
    """Public function with body."""
    x = 1
    y = 2
    return x + y

def _private_function():
    """Private function with body."""
    a = 10
    b = 20
    return a * b
'''

        adapter = make_adapter(PythonCfg(
            strip_function_bodies=FunctionBodyConfig(policy="keep_public")
        ))

        result, meta = adapter.process(lctx(code))

        # Public function body should be preserved
        assert "def public_function():" in result
        assert "x = 1" in result

        # Private function body should be stripped
        assert "def _private_function():" in result
        assert "# … function body omitted" in result
        assert "a = 10" not in result

        assert meta.get("python.removed.function_body", 0) == 1


class TestPythonFunctionBodyEdgeCases:
    """Test edge cases for Python function body optimization."""

    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''def simple(): return 42

def complex():
    x = 1
    y = 2
    return x + y
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        # Single-line function should not be stripped
        assert "def simple(): return 42" in result

        # Multi-line function should be stripped
        assert "def complex():" in result
        assert "# … function body omitted" in result
        assert "x = 1" not in result

    def test_nested_functions(self):
        """Test handling of nested functions."""
        code = '''def outer():
    """Outer function."""
    def inner():
        """Inner function."""
        return "inner"

    result = inner()
    return f"outer: {result}"
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def outer():" in result
        assert '"""Outer function."""' in result
        assert "# … function body omitted" in result

    def test_class_methods(self):
        """Test handling of class methods specifically."""
        code = '''class TestClass:
    def __init__(self):
        self.value = 42
        self.initialized = True

    def public_method(self):
        result = self.value
        return result

    def _private_method(self):
        temp = self.value * 2
        return temp

    @property
    def value_property(self):
        val = self.value
        return val
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def __init__(self):" in result
        assert "def public_method(self):" in result
        assert "def _private_method(self):" in result
        assert "def value_property(self):" in result
        assert "# … method body omitted" in result
        assert "self.initialized = True" not in result


class TestPythonDocstringPreservation:
    """Test preservation of docstrings when stripping function bodies."""

    def test_function_with_docstring_preserved(self):
        """Test that function docstrings are preserved when bodies are stripped."""
        code = '''def calculate_sum(a, b):
    """Calculate the sum of two numbers.

    Args:
        a (int): First number
        b (int): Second number

    Returns:
        int: Sum of a and b
    """
    result = a + b
    print(f"Sum: {result}")
    return result
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def calculate_sum(a, b):" in result
        assert '"""Calculate the sum of two numbers.' in result
        assert 'Args:' in result
        assert 'Returns:' in result

        assert "result = a + b" not in result
        assert "print(f" not in result
        assert "# … function body omitted" in result

    def test_method_with_docstring_preserved(self):
        """Test that method docstrings are preserved when bodies are stripped."""
        code = '''class Calculator:
    def multiply(self, a, b):
        """Multiply two numbers together.

        This method performs multiplication operation.
        """
        temp = a * b
        self.history.append(f"multiply({a}, {b}) = {temp}")
        return temp
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def multiply(self, a, b):" in result
        assert '"""Multiply two numbers together.' in result
        assert 'This method performs multiplication operation.' in result

        assert "temp = a * b" not in result
        assert "self.history.append" not in result
        assert "# … method body omitted" in result

    def test_function_without_docstring_full_removal(self):
        """Test that functions without docstrings have bodies fully removed."""
        code = '''def simple_function():
    # Just a comment, no docstring
    x = 1
    y = 2
    return x + y
'''

        adapter = make_adapter(PythonCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "def simple_function():" in result
        assert "# Just a comment" not in result
        assert "x = 1" not in result
        assert "# … function body omitted" in result


class TestPythonExceptPatterns:
    """Test except_patterns for function body preservation."""

    def test_except_patterns_preserves_matching(self):
        """Test that functions matching except_patterns are preserved."""
        code = '''def __init__(self):
    self.value = 42
    self.ready = True

def setup_database():
    conn = connect()
    return conn

def regular_function():
    x = 1
    y = 2
    return x + y
'''

        adapter = make_adapter(PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="strip_all",
                except_patterns=["^__init__", "^setup_"]
            )
        ))

        result, meta = adapter.process(lctx(code))

        # __init__ and setup_ should be preserved
        assert "self.value = 42" in result
        assert "conn = connect()" in result

        # regular_function should be stripped
        assert "def regular_function():" in result
        assert "# … function body omitted" in result
        assert "x = 1" not in result


class TestPythonKeepAnnotated:
    """Test keep_annotated for function body preservation."""

    def test_keep_annotated_preserves_decorated(self):
        """Test that decorated functions matching keep_annotated are preserved."""
        code = '''@pytest.fixture
def database_connection():
    conn = connect()
    yield conn
    conn.close()

@important
def critical_function():
    do_important_stuff()
    return result

def regular_function():
    x = 1
    y = 2
    return x + y
'''

        adapter = make_adapter(PythonCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="strip_all",
                keep_annotated=["@pytest", "@important"]
            )
        ))

        result, meta = adapter.process(lctx(code))

        # Decorated functions should be preserved
        assert "conn = connect()" in result
        assert "do_important_stuff()" in result

        # regular_function should be stripped
        assert "def regular_function():" in result
        assert "# … function body omitted" in result
        assert "x = 1" not in result
