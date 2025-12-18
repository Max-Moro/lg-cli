"""
Tests for different handling of header vs implementation files in C++ adapter.

This tests the key distinction between .h/.hpp and .cpp files that is specific to C++.
"""

from pathlib import Path

from lg.adapters.cpp import CppCfg
from lg.adapters.code_model import FunctionBodyConfig, ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCppHeaderVsImplementation:
    """Test different optimization strategies for .h/.hpp vs .cpp files."""

    def test_header_file_minimal_optimization(self):
        """Test that header files receive minimal optimization."""
        header_code = '''#ifndef MYLIB_HPP
#define MYLIB_HPP

#include <iostream>
#include <vector>
#include "utils.hpp"

/**
 * Calculate sum of two numbers.
 * This is a very detailed documentation.
 */
int calculateSum(int a, int b);

/**
 * Internal helper function.
 * Should not be visible in public API.
 */
static inline int helper(int x) {
    return x * 2;
}

struct Data {
    int id;
    std::string name;
};

#endif // MYLIB_HPP
'''

        cfg = CppCfg(
            strip_function_bodies=FunctionBodyConfig(mode="non_public"),
            comment_policy="keep_first_sentence",
        )

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(header_code, Path("/test/mylib.hpp")))

        assert "#include <iostream>" in result
        assert '#include "utils.hpp"' in result

        assert "int calculateSum(int a, int b)" in result

        assert "static inline int helper(int x)" in result
        assert "return x * 2;" in result

        assert_golden_match(result, "header_vs_impl", "header_minimal", language="cpp")

    def test_implementation_file_aggressive_optimization(self):
        """Test that implementation files receive aggressive optimization."""
        impl_code = '''#include "mylib.hpp"
#include "internal_utils.hpp"
#include <algorithm>

// Internal helper function
static int internalHelper(int x) {
    int result = x * 2;
    std::cout << "Helper called with " << x << std::endl;
    return result;
}

/**
 * Calculate sum of two numbers.
 * This is the implementation with detailed logic.
 */
int calculateSum(int a, int b) {
    // Validate inputs
    if (a < 0 || b < 0) {
        std::cerr << "Negative numbers not allowed" << std::endl;
        return -1;
    }

    // Calculate result
    int result = a + b;

    // Log the operation
    std::cout << "Sum: " << a << " + " << b << " = " << result << std::endl;

    return result;
}
'''

        cfg = CppCfg(
            strip_function_bodies=FunctionBodyConfig(mode="all"),
            comment_policy="strip_all",
            imports=ImportConfig(policy="strip_local"),
        )

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(impl_code, Path("/test/mylib.cpp")))

        assert "#include <algorithm>" in result
        assert '"mylib.hpp"' not in result
        assert '"internal_utils.hpp"' not in result

        assert "static int internalHelper(int x)" in result
        assert "// … function body omitted" in result
        assert "int result = x * 2;" not in result

        assert "int calculateSum(int a, int b)" in result
        assert "if (a < 0 || b < 0)" not in result

        assert_golden_match(result, "header_vs_impl", "impl_aggressive", language="cpp")

    def test_inline_functions_in_headers_preserved(self):
        """Test that inline function bodies in headers are preserved."""
        header_code = '''#ifndef UTILS_HPP
#define UTILS_HPP

// Inline functions must have bodies in headers
inline int max(int a, int b) {
    return (a > b) ? a : b;
}

inline int min(int a, int b) {
    return (a < b) ? a : b;
}

// Regular function declaration
int complexOperation(int x, int y);

#endif // UTILS_HPP
'''

        cfg = CppCfg(strip_function_bodies=FunctionBodyConfig(mode="non_public"))

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(header_code, Path("/test/utils.hpp")))

        assert "inline int max(int a, int b)" in result
        assert "return (a > b) ? a : b;" in result

        assert "inline int min(int a, int b)" in result
        assert "return (a < b) ? a : b;" in result

        assert "int complexOperation(int x, int y)" in result

    def test_template_definitions_always_preserved(self):
        """Test that template definitions are always preserved in headers."""
        code_with_templates = '''#ifndef CONTAINER_HPP
#define CONTAINER_HPP

#include <vector>
#include <algorithm>

template<typename T>
class Container {
public:
    void add(T item) {
        items.push_back(item);
    }

    T get(size_t index) const {
        return items[index];
    }

private:
    std::vector<T> items;
};

template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}

#endif // CONTAINER_HPP
'''

        cfg = CppCfg(
            strip_function_bodies=FunctionBodyConfig(mode="non_public"),
            comment_policy="strip_all",
        )

        adapter = make_adapter(cfg)

        result_header, _ = adapter.process(lctx(code_with_templates, Path("/test/container.hpp")))

        assert "template<typename T>" in result_header
        assert "void add(T item)" in result_header
        assert "items.push_back(item);" in result_header
        assert "T get(size_t index) const" in result_header

    def test_targeted_config_by_file_type(self):
        """Test using targeted configuration to apply different rules to .h/.hpp vs .cpp files."""
        code = '''#include <iostream>
#include "local.hpp"

int function(int x) {
    int result = x * 2;
    std::cout << "Result: " << result << std::endl;
    return result;
}
'''

        cfg_header = CppCfg(
            strip_function_bodies=False,
            imports=ImportConfig(policy="keep_all"),
        )

        cfg_impl = CppCfg(
            strip_function_bodies=True,
            imports=ImportConfig(policy="strip_local"),
        )

        adapter_header = make_adapter(cfg_header)
        adapter_impl = make_adapter(cfg_impl)

        result_header, _ = adapter_header.process(lctx(code, Path("/test/file.hpp")))
        result_impl, _ = adapter_impl.process(lctx(code, Path("/test/file.cpp")))

        assert "int result = x * 2;" in result_header
        assert "int result = x * 2;" not in result_impl

        assert '#include "local.hpp"' in result_header
        assert '#include "local.hpp"' not in result_impl


class TestCppHeaderSpecificFeatures:
    """Test features specific to C++ header files."""

    def test_header_guards_preserved(self):
        """Test that header guards are always preserved."""
        code = '''#ifndef MY_HEADER_HPP
#define MY_HEADER_HPP

#include <iostream>

int myFunction();

#endif // MY_HEADER_HPP
'''

        cfg = CppCfg(
            imports=ImportConfig(policy="strip_all"),
            comment_policy="strip_all",
        )

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.hpp")))

        assert "#ifndef MY_HEADER_HPP" in result
        assert "#define MY_HEADER_HPP" in result
        assert "#endif" in result

    def test_pragma_once_preserved(self):
        """Test that #pragma once is preserved."""
        code = '''#pragma once

#include <iostream>

int myFunction();
'''

        cfg = CppCfg(imports=ImportConfig(policy="strip_all"))

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.hpp")))

        assert "#pragma once" in result

    def test_extern_cpp_preserved(self):
        """Test that extern C++ blocks are preserved."""
        code = '''#ifdef __cplusplus
extern "C" {
#endif

int cFunction();

#ifdef __cplusplus
}
#endif
'''

        cfg = CppCfg(strip_function_bodies=True)

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.h")))

        assert '#ifdef __cplusplus' in result
        assert 'extern "C"' in result
        assert "int cFunction" in result

    def test_constexpr_in_headers(self):
        """Test that constexpr definitions in headers are preserved."""
        code = '''#pragma once

constexpr int MAX_SIZE = 100;

constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

class Constants {
public:
    static constexpr double PI = 3.14159265359;

    static constexpr int compute() {
        return MAX_SIZE * 2;
    }
};
'''

        cfg = CppCfg(strip_function_bodies=FunctionBodyConfig(mode="non_public"))

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/constants.hpp")))

        assert "constexpr int MAX_SIZE = 100;" in result
        assert "constexpr int factorial(int n)" in result
        assert "return n <= 1 ? 1 : n * factorial(n - 1);" in result
        assert "static constexpr double PI" in result
