"""
Tests for function body optimization in C adapter.
"""

from lg.adapters.c import CCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCFunctionBodyOptimization:
    """Test function body stripping for C code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(CCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("c.removed.function_body", 0) > 0
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_large_only_function_stripping(self, do_function_bodies):
        """Test stripping only large functions."""
        adapter = make_adapter(CCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=5
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert_golden_match(result, "function_bodies", "large_only_strip")

    def test_static_function_handling(self):
        """Test handling of static functions."""
        code = '''static int helper(int x) {
    return x * 2;
}

int public_function(int x) {
    return helper(x);
}
'''

        adapter = make_adapter(CCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "static int helper(int x)" in result
        assert "int public_function(int x)" in result
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "static_functions")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "int test(void) { return 42; }"

        adapter = make_adapter(CCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "return 42;" in result
        assert meta.get("c.removed.function_body", 0) == 0


class TestCFunctionBodyEdgeCases:
    """Test edge cases for C function body optimization."""

    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''int simple(void) { return 42; }

int complex(void) {
    int x = 1;
    int y = 2;
    return x + y;
}
'''

        adapter = make_adapter(CCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "int simple(void) { return 42; }" in result

        assert "int complex(void)" in result
        assert "// … function body omitted" in result
        assert "int x = 1;" not in result

    def test_function_pointers(self):
        """Test handling of function pointer declarations."""
        code = '''typedef void (*Callback)(int);

void process(Callback cb) {
    if (cb) {
        cb(42);
    }
}
'''

        adapter = make_adapter(CCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "typedef void (*Callback)(int);" in result
        assert "void process(Callback cb)" in result

    def test_variadic_functions(self):
        """Test handling of variadic functions."""
        code = '''#include <stdarg.h>

int sum(int count, ...) {
    va_list args;
    va_start(args, count);

    int total = 0;
    for (int i = 0; i < count; i++) {
        total += va_arg(args, int);
    }

    va_end(args);
    return total;
}
'''

        adapter = make_adapter(CCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "int sum(int count, ...)" in result
        assert "// … function body omitted" in result
