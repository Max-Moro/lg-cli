"""
Tests for public API filtering in C adapter.
"""

from lg.adapters.langs.c import CCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestCPublicApiOptimization:
    """Test public API filtering for C code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("c.removed.function", 0) > 0

        assert "UserManager* user_manager_new" in result
        assert "User* user_manager_create_user" in result

        assert "static void validate_user_data" not in result
        assert "static int generate_id" not in result

        assert_golden_match(result, "public_api", "basic")

    def test_static_function_detection(self):
        """Test detection of static functions."""
        code = '''// Public functions
int public_function(int x);
void another_public(void);

// Static (private) functions
static int helper(int x);
static void internal_helper(void);

// Implementations
int public_function(int x) {
    return helper(x);
}

static int helper(int x) {
    return x * 2;
}
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "int public_function(int x)" in result
        assert "void another_public(void)" in result

        assert "static int helper" not in result
        assert "static void internal_helper" not in result

    def test_public_vs_private_structs(self):
        """Test distinction between public and private structures."""
        code = '''// Public structure
typedef struct {
    int id;
    char* name;
} User;

// Static (private) structure
static struct {
    int timeout;
    int retries;
} config;

// File-scope (private) structure
struct InternalData {
    void* ptr;
};
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "typedef struct" in result
        assert "User" in result

    def test_global_vs_static_variables(self):
        """Test filtering of static variables."""
        code = '''// Public global variable
extern int public_counter;

// Public constant
const char* PUBLIC_VERSION = "1.0.0";

// Static (private) variable
static int private_counter = 0;

// Static (private) constant
static const char* PRIVATE_SECRET = "secret";
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "extern int public_counter" in result
        assert "PUBLIC_VERSION" in result

        assert "static int private_counter" not in result
        assert "PRIVATE_SECRET" not in result

    def test_header_guards_preservation(self):
        """Test that header guards are preserved."""
        code = '''#ifndef MY_HEADER_H
#define MY_HEADER_H

int public_function(void);

static int private_function(void);

#endif /* MY_HEADER_H */
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "#ifndef MY_HEADER_H" in result
        assert "#define MY_HEADER_H" in result
        assert "#endif" in result

        assert "int public_function(void)" in result
        assert "static int private_function" not in result


class TestCPublicApiEdgeCases:
    """Test edge cases for C public API filtering."""

    def test_inline_functions(self):
        """Test handling of inline functions."""
        code = '''// Public inline function
inline int max(int a, int b) {
    return (a > b) ? a : b;
}

// Static inline function
static inline int min(int a, int b) {
    return (a < b) ? a : b;
}
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "inline int max(int a, int b)" in result
        assert "static inline int min" not in result

    def test_extern_declarations(self):
        """Test handling of extern declarations."""
        code = '''// External declarations (public)
extern int global_var;
extern void external_function(void);

// Static declarations (private)
static int internal_var;
static void internal_function(void);
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "extern int global_var" in result
        assert "extern void external_function" in result

        assert "static int internal_var" not in result
        assert "static void internal_function" not in result

    def test_macro_definitions(self):
        """Test handling of macro definitions."""
        code = '''// Public macros
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define PUBLIC_CONSTANT 42

// All macros are public in C
#define INTERNAL_HELPER(x) ((x) * 2)
'''

        adapter = make_adapter(CCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "#define MAX(a, b)" in result
        assert "#define PUBLIC_CONSTANT" in result
