"""
Tests for different handling of header vs implementation files in C adapter.

This tests the key distinction between .h and .c files that is specific to C/C++.
"""

from pathlib import Path

from lg.adapters.c import CCfg
from lg.adapters.code_model import FunctionBodyConfig, ImportConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCHeaderVsImplementation:
    """Test different optimization strategies for .h vs .c files."""

    def test_header_file_minimal_optimization(self):
        """Test that header files receive minimal optimization."""
        header_code = '''#ifndef MYLIB_H
#define MYLIB_H

#include <stdio.h>
#include "utils.h"

/**
 * Calculate sum of two numbers.
 * This is a very detailed documentation.
 */
int calculate_sum(int a, int b);

/**
 * Internal helper function.
 * Should not be visible in public API.
 */
static inline int helper(int x) {
    return x * 2;
}

typedef struct {
    int id;
    char name[50];
} Data;

#endif /* MYLIB_H */
'''

        cfg = CCfg(
            strip_function_bodies=FunctionBodyConfig(mode="non_public"),
            comment_policy="keep_first_sentence",
        )

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(header_code, Path("/test/mylib.h")))

        assert "#include <stdio.h>" in result
        assert "#include \"utils.h\"" in result

        assert "int calculate_sum(int a, int b)" in result

        assert "static inline int helper(int x)" in result
        assert "return x * 2;" in result

        assert_golden_match(result, "header_vs_impl", "header_minimal", language="c")

    def test_implementation_file_aggressive_optimization(self):
        """Test that implementation files receive aggressive optimization."""
        impl_code = '''#include "mylib.h"
#include "internal_utils.h"
#include <stdlib.h>

// Internal helper function
static int internal_helper(int x) {
    int result = x * 2;
    printf("Helper called with %d\\n", x);
    return result;
}

/**
 * Calculate sum of two numbers.
 * This is the implementation with detailed logic.
 */
int calculate_sum(int a, int b) {
    // Validate inputs
    if (a < 0 || b < 0) {
        fprintf(stderr, "Negative numbers not allowed\\n");
        return -1;
    }

    // Calculate result
    int result = a + b;

    // Log the operation
    printf("Sum: %d + %d = %d\\n", a, b, result);

    return result;
}
'''

        cfg = CCfg(
            strip_function_bodies=FunctionBodyConfig(mode="all"),
            comment_policy="strip_all",
            imports=ImportConfig(policy="strip_local"),
        )

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(impl_code, Path("/test/mylib.c")))

        assert "#include <stdlib.h>" in result
        assert '"mylib.h"' not in result
        assert '"internal_utils.h"' not in result

        assert "static int internal_helper(int x)" in result
        assert "// … function body omitted" in result
        assert "int result = x * 2;" not in result

        assert "int calculate_sum(int a, int b)" in result
        assert "if (a < 0 || b < 0)" not in result

        assert_golden_match(result, "header_vs_impl", "impl_aggressive", language="c")

    def test_inline_functions_in_headers_preserved(self):
        """Test that inline function bodies in headers are preserved."""
        header_code = '''#ifndef UTILS_H
#define UTILS_H

// Inline functions must have bodies in headers
static inline int max(int a, int b) {
    return (a > b) ? a : b;
}

static inline int min(int a, int b) {
    return (a < b) ? a : b;
}

// Regular function declaration
int complex_operation(int x, int y);

#endif /* UTILS_H */
'''

        cfg = CCfg(strip_function_bodies=FunctionBodyConfig(mode="non_public"))

        adapter = make_adapter(cfg)

        result, meta = adapter.process(lctx(header_code, Path("/test/utils.h")))

        assert "static inline int max(int a, int b)" in result
        assert "return (a > b) ? a : b;" in result

        assert "static inline int min(int a, int b)" in result
        assert "return (a < b) ? a : b;" in result

        assert "int complex_operation(int x, int y)" in result

    def test_macros_always_preserved(self):
        """Test that macros are always preserved in both headers and implementation."""
        code_with_macros = '''#define MAX_SIZE 1024
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define DEBUG_PRINT(msg) printf("[DEBUG] %s\\n", msg)

void process_data(void) {
    int size = MAX_SIZE;
    DEBUG_PRINT("Processing");
}
'''

        cfg = CCfg(
            strip_function_bodies=True,
            comment_policy="strip_all",
        )

        adapter = make_adapter(cfg)

        result_header, _ = adapter.process(lctx(code_with_macros, Path("/test/file.h")))
        result_impl, _ = adapter.process(lctx(code_with_macros, Path("/test/file.c")))

        for result in [result_header, result_impl]:
            assert "#define MAX_SIZE 1024" in result
            assert "#define MIN(a, b)" in result
            assert "#define DEBUG_PRINT(msg)" in result

    def test_targeted_config_by_file_type(self):
        """Test using targeted configuration to apply different rules to .h vs .c files."""
        code = '''#include <stdio.h>
#include "local.h"

int function(int x) {
    int result = x * 2;
    printf("Result: %d\\n", result);
    return result;
}
'''

        cfg_header = CCfg(
            strip_function_bodies=False,
            imports=ImportConfig(policy="keep_all"),
        )

        cfg_impl = CCfg(
            strip_function_bodies=True,
            imports=ImportConfig(policy="strip_local"),
        )

        adapter_header = make_adapter(cfg_header)
        adapter_impl = make_adapter(cfg_impl)

        result_header, _ = adapter_header.process(lctx(code, Path("/test/file.h")))
        result_impl, _ = adapter_impl.process(lctx(code, Path("/test/file.c")))

        assert "int result = x * 2;" in result_header
        assert "int result = x * 2;" not in result_impl

        assert '#include "local.h"' in result_header
        assert '#include "local.h"' not in result_impl


class TestCHeaderSpecificFeatures:
    """Test features specific to C header files."""

    def test_header_guards_preserved(self):
        """Test that header guards are always preserved."""
        code = '''#ifndef MY_HEADER_H
#define MY_HEADER_H

#include <stdio.h>

int my_function(void);

#endif /* MY_HEADER_H */
'''

        cfg = CCfg(
            imports=ImportConfig(policy="strip_all"),
            comment_policy="strip_all",
        )

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.h")))

        assert "#ifndef MY_HEADER_H" in result
        assert "#define MY_HEADER_H" in result
        assert "#endif" in result

    def test_pragma_once_preserved(self):
        """Test that #pragma once is preserved."""
        code = '''#pragma once

#include <stdio.h>

int my_function(void);
'''

        cfg = CCfg(imports=ImportConfig(policy="strip_all"))

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.h")))

        assert "#pragma once" in result

    def test_extern_c_preserved(self):
        """Test that extern C blocks are preserved."""
        code = '''#ifdef __cplusplus
extern "C" {
#endif

int c_function(void);

#ifdef __cplusplus
}
#endif
'''

        cfg = CCfg(strip_function_bodies=True)

        adapter = make_adapter(cfg)

        result, _ = adapter.process(lctx(code, Path("/test/my_header.h")))

        assert '#ifdef __cplusplus' in result
        assert 'extern "C"' in result
        assert "int c_function(void)" in result
