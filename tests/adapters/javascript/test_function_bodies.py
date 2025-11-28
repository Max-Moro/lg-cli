"""
Tests for function body optimization in JavaScript adapter.
"""

from lg.adapters.javascript import JavaScriptCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_js, do_function_bodies, assert_golden_match, make_adapter


class TestJavaScriptFunctionBodyOptimization:
    """Test function body stripping for JavaScript code."""

    def test_basic_function_stripping(self, do_function_bodies, lctx_js):
        """Test basic function body stripping."""
        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(do_function_bodies))

        # Check that functions were processed
        assert meta.get("javascript.removed.function_body", 0) > 0
        assert meta.get("javascript.removed.method_body", 0) > 0
        assert "// … method body omitted" in result
        assert "// … function body omitted" in result

        # Golden file test
        assert_golden_match(result, "function_bodies", "basic_strip")

    def test_large_only_method_stripping(self, do_function_bodies, lctx_js):
        """Test stripping only large methods."""
        adapter = make_adapter(JavaScriptCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=4
            )
        ))

        result, meta = adapter.process(lctx_js(do_function_bodies))

        # Should have fewer removals than basic test
        assert_golden_match(result, "function_bodies", "large_only_strip")

    def test_arrow_function_handling(self, lctx_js):
        """Test handling of arrow functions."""
        arrow_code = '''
const simple = () => "simple";

const complex = (data) => {
    const processed = data
        .filter(item => item.length > 0)
        .map(item => item.trim())
        .sort();

    return processed.join(', ');
};

const multiline = (users) => {
    return users
        .filter(u => u.active)
        .map(u => u.name)
        .sort();
};
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(arrow_code))

        # Should only strip multiline arrow functions
        assert 'const simple = () => "simple";' in result  # Single line preserved

        # Arrow functions signatures preserved
        assert "const complex = (data) =>" in result
        assert "const multiline = (users) =>" in result

        assert_golden_match(result, "function_bodies", "arrow_functions")

    def test_class_method_preservation(self, lctx_js):
        """Test that class structure is preserved while stripping method bodies."""
        class_code = '''
export class Calculator {
    constructor(name) {
        this.name = name;
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }

    getHistory() {
        return [...this.history];
    }
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(class_code))

        # Class structure should be preserved
        assert "export class Calculator {" in result

        # Methods should be stripped but signatures preserved
        assert "add(a, b)" in result
        assert "getHistory()" in result

        assert_golden_match(result, "function_bodies", "class_methods")

    def test_no_stripping_preserves_original(self, lctx_js):
        """Test that disabling stripping preserves original code."""
        code = "function test() { return 42; }"

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=False))

        result, meta = adapter.process(lctx_js(code))

        # Should be nearly identical to original
        assert "return 42;" in result
        assert meta.get("javascript.removed.function_body", 0) == 0
        assert meta.get("javascript.removed.method_bodies", 0) == 0

    def test_public_only_method_stripping(self, lctx_js):
        """Test public_only mode for JavaScript method body stripping."""
        code = '''export class Calculator {
    add(a, b) {
        const result = a + b;
        console.log("Adding", a, b);
        return result;
    }

    #multiply(a, b) {
        const result = a * b;
        console.log("Multiplying", a, b);
        return result;
    }
}
'''

        function_config = FunctionBodyConfig(mode="public_only")
        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=function_config))

        result, meta = adapter.process(lctx_js(code))

        # Public method body should be stripped
        assert "add(a, b)" in result
        assert "// … method body omitted" in result
        assert "const result = a + b;" not in result

        # Private method body should be preserved (it's not public)
        assert "#multiply(a, b)" in result
        assert "const result = a * b;" in result


class TestJavaScriptFunctionBodyEdgeCases:
    """Test edge cases for JavaScript function body optimization."""

    def test_single_line_functions(self, lctx_js):
        """Test that single-line functions are handled correctly."""
        code = '''function simple() { return 42; }

function complex() {
    const x = 1;
    const y = 2;
    return x + y;
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Single-line function should not be stripped
        assert "function simple() { return 42; }" in result

        # Multi-line function should be stripped
        assert "function complex()" in result
        assert "// … function body omitted" in result
        assert "const x = 1;" not in result

    def test_nested_functions(self, lctx_js):
        """Test handling of nested functions."""
        code = '''function outer() {
    function inner() {
        return "inner";
    }

    const result = inner();
    return `outer: ${result}`;
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Outer function body should be stripped
        assert "function outer()" in result
        assert "// … function body omitted" in result
        assert "function inner():" not in result  # Should be part of stripped body


class TestJavaScriptJSDocPreservation:
    """Test preservation of JSDoc when stripping function bodies."""

    def test_function_with_jsdoc_preserved(self, lctx_js):
        """Test that function JSDoc is preserved when bodies are stripped."""
        code = '''/**
 * Calculate the sum of two numbers.
 *
 * @param {number} a First number
 * @param {number} b Second number
 * @returns {number} Sum of a and b
 */
function calculateSum(a, b) {
    // This is a comment
    const result = a + b;
    console.log("Sum:", result);
    return result;
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Function signature should be preserved
        assert "function calculateSum(a, b)" in result

        # JSDoc should be preserved completely
        assert "/**" in result and "Calculate the sum of two numbers" in result
        assert "@param" in result
        assert "@returns" in result

        # Function body should be removed
        assert "const result = a + b;" not in result
        assert "console.log" not in result
        assert "return result;" not in result

        # Should have placeholder for removed body
        assert "// … function body omitted" in result

    def test_method_with_jsdoc_preserved(self, lctx_js):
        """Test that method JSDoc is preserved when bodies are stripped."""
        code = '''class Calculator {
    /**
     * Multiply two numbers together.
     *
     * This method performs multiplication operation.
     */
    multiply(a, b) {
        const temp = a * b;
        this.history.push(`multiply(${a}, ${b}) = ${temp}`);
        return temp;
    }
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Method signature should be preserved
        assert "multiply(a, b)" in result

        # JSDoc should be preserved
        assert "/**" in result and "Multiply two numbers together" in result
        assert "This method performs multiplication operation" in result

        # Method body should be removed
        assert "const temp = a * b;" not in result
        assert "this.history.push" not in result
        assert "return temp;" not in result

        # Should have placeholder for removed body
        assert "// … method body omitted" in result

    def test_function_without_jsdoc_full_removal(self, lctx_js):
        """Test that functions without JSDoc have bodies fully removed."""
        code = '''function simpleFunction() {
    // Just a comment, no JSDoc
    const x = 1;
    const y = 2;
    return x + y;
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Function signature should be preserved
        assert "function simpleFunction()" in result

        # Everything else should be removed
        assert "// Just a comment" not in result
        assert "const x = 1;" not in result
        assert "return x + y;" not in result

        # Should have placeholder
        assert "// … function body omitted" in result

    def test_mixed_functions_with_without_jsdoc(self, lctx_js):
        """Test mixed functions - some with JSDoc, some without."""
        code = '''/**
 * This function has documentation.
 */
function documentedFunction() {
    const complexLogic = true;
    if (complexLogic) {
        return "documented";
    }
    return "fallback";
}

function undocumentedFunction() {
    // No JSDoc here
    const simpleReturn = "undocumented";
    return simpleReturn;
}
'''

        adapter = make_adapter(JavaScriptCfg(strip_function_bodies=True))

        result, meta = adapter.process(lctx_js(code))

        # Both function signatures should be preserved
        assert "function documentedFunction()" in result
        assert "function undocumentedFunction()" in result

        # Only the JSDoc should be preserved
        assert "/**" in result and "This function has documentation" in result
        assert "// No JSDoc here" not in result

        # All logic should be removed
        assert "const complexLogic" not in result
        assert "const simpleReturn" not in result
        assert 'return "documented"' not in result
        assert 'return "undocumented"' not in result

        # Should have placeholders
        assert "// … function body omitted" in result
