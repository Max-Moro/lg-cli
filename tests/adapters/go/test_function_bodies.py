"""
Tests for function body optimization in Go adapter.
"""

from lg.adapters.go import GoCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestGoFunctionBodyOptimization:
    """Test function body stripping for Go code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(GoCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("go.removed.function_body", 0) > 0
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip", language="go")

    def test_max_tokens_trimming(self, do_function_bodies):
        """Test trimming function bodies to token budget."""
        adapter = make_adapter(GoCfg(
            strip_function_bodies=FunctionBodyConfig(
                policy="keep_all",
                max_tokens=20
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert_golden_match(result, "function_bodies", "max_tokens_trim", language="go")

    def test_method_handling(self):
        """Test handling of methods with receivers."""
        code = '''package main

func (c *Calculator) Add(a, b int) int {
    result := a + b
    c.history = append(c.history, result)
    return result
}

func (c *Calculator) Multiply(a, b int) int {
    result := a * b
    c.history = append(c.history, result)
    return result
}
'''

        adapter = make_adapter(GoCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "func (c *Calculator) Add(a, b int) int" in result
        assert "func (c *Calculator) Multiply(a, b int) int" in result
        assert "// … method body omitted" in result

        assert_golden_match(result, "function_bodies", "methods", language="go")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "func test() int { return 42 }"

        adapter = make_adapter(GoCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "return 42" in result
        assert meta.get("go.removed.function_body", 0) == 0


class TestGoFunctionBodyEdgeCases:
    """Test edge cases for Go function body optimization."""

    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''package main

func simple() int { return 42 }

func complex() int {
    x := 1
    y := 2
    return x + y
}
'''

        adapter = make_adapter(GoCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "func simple() int { return 42 }" in result

        assert "func complex() int" in result
        assert "// … function body omitted" in result
        assert "x := 1" not in result

    def test_variadic_functions(self):
        """Test handling of variadic functions."""
        code = '''package main

func sum(nums ...int) int {
    total := 0
    for _, num := range nums {
        total += num
    }
    return total
}
'''

        adapter = make_adapter(GoCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "func sum(nums ...int) int" in result
        assert "// … function body omitted" in result

    def test_interface_methods(self):
        """Test that interface method signatures are preserved."""
        code = '''package main

type Reader interface {
    Read(p []byte) (n int, err error)
    Close() error
}

type Writer interface {
    Write(p []byte) (n int, err error)
}
'''

        adapter = make_adapter(GoCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "type Reader interface" in result
        assert "Read(p []byte) (n int, err error)" in result
        assert "Close() error" in result
