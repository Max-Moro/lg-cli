"""
Tests for function body optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import lctx_ts, do_function_bodies, assert_golden_match, make_adapter


class TestTypeScriptFunctionBodyOptimization:
    """Test function body stripping for TypeScript code."""
    
    def test_basic_function_stripping(self, do_function_bodies):
        """Test basic function body stripping."""
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(do_function_bodies))
        
        # Check that functions were processed
        assert meta.get("typescript.removed.function_body", 0) == 6
        assert meta.get("typescript.removed.method_body", 0) == 5
        assert "// … method body omitted (11 lines)" in result
        assert "// … function body omitted (13 lines)" in result
        
        # Golden file test
        assert_golden_match(result, "function_bodies", "basic_strip")
    
    def test_large_only_method_stripping(self, do_function_bodies):
        """Test stripping only large methods."""
        adapter = make_adapter(TypeScriptCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=4  # Higher threshold for TypeScript
            )
        ))
        
        result, meta = adapter.process(lctx_ts(do_function_bodies))
        
        # Should have fewer removals than basic test
        assert_golden_match(result, "function_bodies", "large_only_strip")
    
    def test_arrow_function_handling(self):
        """Test handling of arrow functions."""
        arrow_code = '''
const simple = () => "hello";

const complex = (a, b) => {
    const result = a + b;
    console.log("Computing:", result);
    return result;
};

const multiline = (users) => {
    return users
        .filter(u => u.active)
        .map(u => u.name)
        .sort();
};
'''
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(arrow_code))
        
        # Should only strip multiline arrow functions (complex and multiline)
        assert 'const simple = () => "hello";' in result  # Single line preserved
        
        # Count placeholders to verify stripping occurred
        placeholder_count = result.count("// … function body omitted")

        # Arrow functions signatures preserved
        assert "const complex = (a, b) =>" in result
        assert "const multiline = (users) =>" in result

        # We expect 2 multiline arrow functions to be stripped
        expected_stripped = 2
        assert meta.get("typescript.removed.function_body", 0) == placeholder_count == expected_stripped

        assert_golden_match(result, "function_bodies", "arrow_functions")
    
    def test_class_method_preservation(self):
        """Test that class structure is preserved while stripping method bodies."""
        class_code = '''
export class Calculator {
    private history: string[] = [];
    
    constructor(name: string) {
        this.name = name;
        this.history = [];
    }
    
    add(a: number, b: number): number {
        const result = a + b;
        this.history.push(`${a} + ${b} = ${result}`);
        return result;
    }
    
    getHistory(): string[] {
        return [...this.history];
    }
}
'''
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(class_code))
        
        # Class structure should be preserved
        assert "export class Calculator {" in result
        assert "private history: string[] = [];" in result
        
        # Methods should be stripped but signatures preserved
        assert "add(a: number, b: number): number" in result
        assert "getHistory(): string[]" in result
        
        assert_golden_match(result, "function_bodies", "class_methods")
    
    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "function test() { return 42; }"
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=False))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should be nearly identical to original
        assert "return 42;" in result
        assert meta.get("typescript.removed.function_body", 0) == 0
        assert meta.get("typescript.removed.method_bodies", 0) == 0

    def test_public_only_method_stripping(self):
        """Test public_only mode for TypeScript method body stripping."""
        code = '''export class Calculator {
    public add(a: number, b: number): number {
        const result = a + b;
        console.log("Adding", a, b);
        return result;
    }
    
    private multiply(a: number, b: number): number {
        const result = a * b;
        console.log("Multiplying", a, b);
        return result;
    }
}
'''
        
        function_config = FunctionBodyConfig(mode="public_only")
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=function_config))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Public method body should be stripped
        assert "public add(a: number, b: number): number" in result
        assert "// … method body omitted" in result
        assert "const result = a + b;" not in result
        
        # Private method body should be preserved (it's not public)
        assert "private multiply(a: number, b: number): number" in result
        assert "const result = a * b;" in result


class TestTypeScriptFunctionBodyEdgeCases:
    """Test edge cases for TypeScript function body optimization."""
    
    def test_single_line_functions(self):
        """Test that single-line functions are handled correctly."""
        code = '''function simple() { return 42; }

function complex(): number {
    const x = 1;
    const y = 2;
    return x + y;
}
'''
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Single-line function should not be stripped (important for simple functions)
        assert "function simple() { return 42; }" in result
        
        # Multi-line function should be stripped
        assert "function complex(): number" in result
        assert "// … function body omitted" in result
        assert "const x = 1;" not in result
    
    def test_nested_functions(self):
        """Test handling of nested functions."""
        code = '''function outer(): string {
    function inner(): string {
        return "inner";
    }
    
    const result = inner();
    return `outer: ${result}`;
}
'''
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Outer function body should be stripped
        assert "function outer(): string" in result
        assert "// … function body omitted" in result
        assert "function inner():" not in result  # Should be part of stripped body
    
    def test_interface_and_type_preservation(self):
        """Test that interfaces and types are preserved."""
        code = '''interface User {
    id: number;
    name: string;
}

type UserResponse = {
    user: User;
    success: boolean;
};

function processUser(user: User): UserResponse {
    return {
        user: user,
        success: true
    };
}
'''
        
        adapter = make_adapter(TypeScriptCfg(strip_function_bodies=True))
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Interfaces and types should be preserved
        assert "interface User {" in result
        assert "type UserResponse = {" in result
        assert "id: number;" in result
        assert "name: string;" in result
        
        # Function body should be stripped
        assert "function processUser(user: User): UserResponse" in result
        assert "// … function body omitted" in result
        assert "return {" not in result
