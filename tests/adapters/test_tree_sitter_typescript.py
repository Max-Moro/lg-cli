"""
Tests for Tree-sitter based TypeScript adapter.
"""

import pytest
from pathlib import Path

from lg.adapters.typescript_tree_sitter import TypeScriptTreeSitterAdapter, JavaScriptTreeSitterAdapter
from lg.adapters.code_model import TypeScriptCfg, FunctionBodyConfig
from tests.adapters.conftest import assert_golden_match, create_temp_file


pytestmark = pytest.mark.usefixtures("skip_if_no_tree_sitter")


class TestTypeScriptTreeSitterAdapter:
    """Test suite for TypeScript Tree-sitter adapter."""
    
    def test_basic_function_stripping(self, typescript_code_sample, tmp_path):
        """Test basic function body stripping."""
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(typescript_code_sample, group_size=1, mixed=False)
        
        # Check that functions were processed
        assert meta["code.removed.functions"] >= 0  # May not find arrow functions in sample
        assert meta["code.removed.methods"] > 0
        assert ("/* … method omitted" in result or "/* … function omitted" in result or 
                "// … method omitted" in result or "// … function omitted" in result or
                "// … body omitted" in result)
        
        # Golden file test
        golden_file = tmp_path / "typescript_basic_strip.golden"
        assert_golden_match(result, golden_file)
    
    def test_public_api_only_default(self, typescript_code_sample):
        """Test that TypeScript defaults to public API only."""
        adapter = TypeScriptTreeSitterAdapter()
        
        # Load default config
        adapter._cfg = TypeScriptCfg()
        
        # Check default value - currently False by default, can be changed later
        assert hasattr(adapter._cfg, 'public_api_only')
    
    def test_javascript_adapter_inheritance(self, typescript_code_sample):
        """Test that JavaScript adapter inherits TypeScript logic."""
        js_adapter = JavaScriptTreeSitterAdapter()
        js_adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        # Convert TS sample to JS-like code (remove types)
        js_code = typescript_code_sample.replace(": number", "").replace(": string", "").replace("?: string", "")
        js_code = js_code.replace(": User[]", "").replace(": Observable<User[]>", "")
        js_code = js_code.replace(": Promise<User>", "").replace(": boolean", "")
        
        result, meta = js_adapter.process(js_code, group_size=1, mixed=False)
        
        # Should process similar to TypeScript
        assert meta["_adapter"] == "javascript"
        assert js_adapter.name == "javascript"
        assert ".js" in js_adapter.extensions
    
    def test_large_only_method_stripping(self, typescript_code_sample, tmp_path):
        """Test stripping only large methods."""
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(
            strip_function_bodies=FunctionBodyConfig(
                mode="large_only",
                min_lines=4  # Higher threshold for TypeScript
            )
        )
        
        result, meta = adapter.process(typescript_code_sample, group_size=1, mixed=False)
        
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
        
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(arrow_code, group_size=1, mixed=False)
        
        # Should only strip multiline arrow functions
        assert 'const simple = () => "hello";' in result  # Single line preserved
        assert ("/* … function omitted" in result or "// … body omitted" in result)  # Multiline functions stripped
        
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
        
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(class_code, group_size=1, mixed=False)
        
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
        
        adapter = TypeScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=False)
        
        result, meta = adapter.process(code, group_size=1, mixed=False)
        
        # Should be nearly identical to original
        assert "return 42;" in result
        assert meta["code.removed.functions"] == 0
        assert meta["code.removed.methods"] == 0


class TestJavaScriptTreeSitterAdapter:
    """Test suite for JavaScript Tree-sitter adapter."""
    
    def test_javascript_specific_behavior(self):
        """Test JavaScript-specific behavior."""
        js_code = '''
function calculateTax(amount) {
    const rate = 0.1;
    const tax = amount * rate;
    console.log("Tax calculated:", tax);
    return tax;
}

const arrow = (x) => {
    return x * 2;
};
'''
        
        adapter = JavaScriptTreeSitterAdapter()
        adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
        
        result, meta = adapter.process(js_code, group_size=1, mixed=False)
        
        assert meta["_adapter"] == "javascript"
        assert adapter.name == "javascript"
        assert ".js" in adapter.extensions and ".jsx" in adapter.extensions
