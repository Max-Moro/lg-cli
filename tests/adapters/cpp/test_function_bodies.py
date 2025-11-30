"""
Tests for function body optimization in C++ adapter.
"""

from lg.adapters.cpp import CppCfg
from lg.adapters.code_model import FunctionBodyConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCppFunctionBodyOptimization:
    """Test function body stripping for C++ code."""

    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert meta.get("cpp.removed.function_body", 0) > 0
        assert "// … function body omitted" in result

        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_large_only_function_stripping(self, do_function_bodies):
        """Test stripping only large functions."""
        adapter = make_adapter(CppCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=5
            )
        ))

        result, meta = adapter.process(lctx(do_function_bodies))

        assert_golden_match(result, "function_bodies", "large_only_strip")

    def test_member_function_handling(self):
        """Test handling of class member functions."""
        code = '''class Calculator {
private:
    int value;

public:
    Calculator() : value(0) {}

    int add(int x) {
        value += x;
        return value;
    }

    int get() const {
        return value;
    }
};
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "class Calculator" in result
        assert "int add(int x)" in result
        assert "int get() const" in result
        assert "// … method body omitted" in result

        assert_golden_match(result, "function_bodies", "member_functions")

    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "int test() { return 42; }"

        adapter = make_adapter(CppCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx(code))

        assert "return 42;" in result
        assert meta.get("cpp.removed.function_body", 0) == 0


class TestCppFunctionBodyEdgeCases:
    """Test edge cases for C++ function body optimization."""

    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''int simple() { return 42; }

int complex() {
    int x = 1;
    int y = 2;
    return x + y;
}
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "int simple() { return 42; }" in result

        assert "int complex()" in result
        assert "// … function body omitted" in result
        assert "int x = 1;" not in result

    def test_template_functions(self):
        """Test handling of template functions."""
        code = '''template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}

template<typename T>
class Container {
public:
    void add(T item) {
        items.push_back(item);
    }
private:
    std::vector<T> items;
};
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "template<typename T>" in result
        assert "T max(T a, T b)" in result
        assert "class Container" in result

    def test_inline_functions(self):
        """Test handling of inline functions."""
        code = '''inline int square(int x) {
    return x * x;
}

class Math {
public:
    inline static int cube(int x) {
        return x * x * x;
    }
};
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "inline int square(int x)" in result
        assert "inline static int cube(int x)" in result

    def test_constexpr_functions(self):
        """Test handling of constexpr functions."""
        code = '''constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

class Constants {
public:
    static constexpr int MAX_SIZE = 100;
    static constexpr int compute() {
        return MAX_SIZE * 2;
    }
};
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "constexpr int factorial(int n)" in result
        assert "static constexpr int compute()" in result

    def test_lambda_expressions(self):
        """Test handling of lambda expressions."""
        code = '''void process() {
    auto lambda = [](int x) {
        return x * 2;
    };

    std::for_each(vec.begin(), vec.end(), [&](int x) {
        sum += x;
    });
}
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "void process()" in result

    def test_operator_overloading(self):
        """Test handling of operator overloading."""
        code = '''class Complex {
public:
    Complex operator+(const Complex& other) {
        return Complex(real + other.real, imag + other.imag);
    }

    friend std::ostream& operator<<(std::ostream& os, const Complex& c) {
        os << c.real << " + " << c.imag << "i";
        return os;
    }
private:
    double real, imag;
};
'''

        adapter = make_adapter(CppCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx(code))

        assert "Complex operator+(const Complex& other)" in result
        assert "friend std::ostream& operator<<" in result
