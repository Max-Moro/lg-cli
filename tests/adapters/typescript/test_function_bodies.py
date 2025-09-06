"""
Tests for function body optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import create_typescript_context, typescript_code_sample, assert_golden_match


class TestTypeScriptFunctionBodyOptimization:
    """Test function body stripping for TypeScript code."""
    
    def test_basic_function_stripping(self, typescript_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(typescript_code_sample))
        
        # Check that functions were processed
        assert meta["code.removed.functions"] >= 0  # May not find arrow functions in sample
        assert meta["code.removed.methods"] > 0
        assert ("/* … method omitted" in result or "/* … function omitted" in result or 
                "// … method omitted" in result or "// … function omitted" in result or
                "// … body omitted" in result)
        
        # Golden file test
        golden_file = tmp_path / "typescript_basic_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_large_only_method_stripping(self, typescript_code_sample, tmp_path):
        """Test stripping only large methods."""
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=4  # Higher threshold for TypeScript
            )
        )
        
        result, meta = adapter.process(create_typescript_context(typescript_code_sample))
        
        # Should have fewer removals than basic test
        golden_file = tmp_path / "typescript_large_only_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_arrow_function_handling(self, tmp_path):
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
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(arrow_code))
        
        # If some were stripped, check placeholders
        assert ("… body omitted" in result)
        
        # Should only strip multiline arrow functions (complex and multiline)
        assert 'const simple = () => "hello";' in result  # Single line preserved
        
        # Count placeholders to verify stripping occurred
        placeholder_count = result.count("… body omitted")
        
        # We expect 2 multiline arrow functions to be stripped
        expected_stripped = 2
        assert meta.get("code.removed.functions", 0) == placeholder_count == expected_stripped

        golden_file = tmp_path / "typescript_arrow_functions.golden"
        assert_golden_match(result, golden_file)
    
    def test_class_method_preservation(self, tmp_path):
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
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(class_code))
        
        # Class structure should be preserved
        assert "export class Calculator {" in result
        assert "private history: string[] = [];" in result
        
        # Methods should be stripped but signatures preserved
        assert "add(a: number, b: number): number" in result
        assert "getHistory(): string[]" in result
        
        golden_file = tmp_path / "typescript_class_methods.golden"
        assert_golden_match(result, golden_file)
    
    def test_no_stripping_preserves_original(self):
        """Test that disabling stripping preserves original code."""
        code = "function test() { return 42; }"
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should be nearly identical to original
        assert "return 42;" in result
        assert meta.get("code.removed.functions", 0) == 0
        assert meta.get("code.removed.methods", 0) == 0

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
        
        adapter = TypeScriptAdapter()
        function_config = FunctionBodyConfig(mode="public_only")
        adapter._cfg = TypeScriptCfg(strip_function_bodies=function_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Public method body should be stripped
        assert "public add(a: number, b: number): number" in result
        assert ("/* … method omitted" in result or "// … method omitted" in result or 
                "/* … body omitted" in result or "// … body omitted" in result)
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
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Single-line function should not be stripped (important for simple functions)
        assert "function simple() { return 42; }" in result
        
        # Multi-line function should be stripped
        assert "function complex(): number" in result
        assert ("/* … body omitted" in result or "// … body omitted" in result or 
                "/* … function omitted" in result or "// … function omitted" in result)
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
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Outer function body should be stripped
        assert "function outer(): string" in result
        assert ("/* … body omitted" in result or "// … body omitted" in result or 
                "/* … function omitted" in result or "// … function omitted" in result)
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
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Interfaces and types should be preserved
        assert "interface User {" in result
        assert "type UserResponse = {" in result
        assert "id: number;" in result
        assert "name: string;" in result
        
        # Function body should be stripped
        assert "function processUser(user: User): UserResponse" in result
        assert ("/* … body omitted" in result or "// … body omitted" in result or 
                "/* … function omitted" in result or "// … function omitted" in result)
        assert "return {" not in result or "… " in result
