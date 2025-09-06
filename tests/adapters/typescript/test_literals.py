"""
Tests for literal trimming in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import create_typescript_context


class TestTypeScriptLiteralTrimming:
    """Test literal trimming for TypeScript code."""
    
    def test_string_trimming(self):
        """Test string trimming in TypeScript."""
        code = '''
const shortMsg = "Hello";

const longMsg = "This is a very long TypeScript string that should be trimmed when it exceeds the configured maximum length";

function getMessage(): string {
    return longMsg;
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_string_length=40)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Short string should be preserved
        assert 'const shortMsg = "Hello";' in result
        
        # Long string should be trimmed
        assert "This is a very long TypeScript string..." in result or meta.get("code.removed.literals", 0) > 0
        assert "exceeds the configured maximum length" not in result
    
    def test_template_string_trimming(self):
        """Test template string trimming in TypeScript."""
        code = '''
const name = "user";
const shortTemplate = `Hello ${name}`;

const longTemplate = `
This is a very long template string
that contains multiple lines and 
should be trimmed when it exceeds
the configured limits for templates
`;

function formatMessage(): string {
    return longTemplate;
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_literal_lines=3)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Short template should be preserved
        assert "const shortTemplate = `Hello ${name}`;" in result
        
        # Long template should be trimmed
        assert "// ... string data" in result or meta.get("code.removed.literals", 0) > 0
        assert "should be trimmed when it exceeds" not in result
    
    def test_array_trimming(self):
        """Test array trimming in TypeScript."""
        code = '''
const small: number[] = [1, 2, 3];

const large: string[] = [
    "element1", "element2", "element3", "element4",
    "element5", "element6", "element7", "element8",
    "element9", "element10"
];

function getItems(): string[] {
    return large;
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_array_elements=6)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Small array should be preserved
        assert "const small: number[] = [1, 2, 3];" in result
        
        # Large array should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        assert "element10" not in result or meta.get("code.removed.literals", 0) > 0
    
    def test_object_trimming(self):
        """Test object trimming in TypeScript."""
        code = '''
interface Config {
    debug: boolean;
    version: string;
    features: string[];
}

const smallConfig = { debug: true, version: "1.0" };

const largeConfig: Config = {
    debug: true,
    version: "2.0",
    apiUrl: "https://api.example.com",
    timeout: 5000,
    retries: 3,
    features: ["auth", "logging", "metrics"],
    experimental: {
        newFeature: true,
        betaMode: false
    }
};

function getConfig(): Config {
    return largeConfig;
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_object_properties=4)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Small object should be preserved
        assert 'const smallConfig = { debug: true, version: "1.0" };' in result
        
        # Large object should be trimmed
        assert ("... and" in result and "more}" in result) or meta.get("code.removed.literals", 0) > 0


class TestTypeScriptLiteralEdgeCases:
    """Test edge cases for TypeScript literal trimming."""
    
    def test_empty_literals(self):
        """Test handling of empty TypeScript literals."""
        code = '''
const emptyString = "";
const emptyArray: string[] = [];
const emptyObject: {} = {};
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(
            max_string_length=10,
            max_array_elements=5,
            max_object_properties=3
        )
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Empty literals should be preserved (they're within limits)
        assert 'const emptyString = "";' in result
        assert "const emptyArray: string[] = [];" in result
        assert "const emptyObject: {} = {};" in result
        
        # No trimming should occur
        assert meta.get("code.removed.literals", 0) == 0
    
    def test_nested_literals(self):
        """Test handling of nested TypeScript literal structures."""
        code = '''
const nested = {
    users: [
        { name: "Alice", age: 30, email: "alice@example.com" },
        { name: "Bob", age: 25, email: "bob@example.com" },
        { name: "Charlie", age: 35, email: "charlie@example.com" }
    ],
    settings: {
        theme: "dark",
        language: "en",
        notifications: true
    }
};
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_literal_lines=3)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Nested structure should be trimmed due to line count
        assert "// ... object data" in result or meta.get("code.removed.literals", 0) > 0
        assert "alice@example.com" not in result or "..." in result
    
    def test_type_annotations_preserved(self):
        """Test that type annotations are preserved during literal trimming."""
        code = '''
const users: User[] = [
    { id: 1, name: "Alice", email: "alice@example.com" },
    { id: 2, name: "Bob", email: "bob@example.com" },
    { id: 3, name: "Charlie", email: "charlie@example.com" },
    { id: 4, name: "David", email: "david@example.com" },
    { id: 5, name: "Eve", email: "eve@example.com" }
];

const config: AppConfig = {
    apiUrl: "https://api.example.com",
    timeout: 5000,
    retries: 3,
    debug: true,
    features: ["auth", "logging"]
};
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_array_elements=3, max_object_properties=3)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Type annotations should be preserved
        assert "const users: User[] =" in result
        assert "const config: AppConfig =" in result
        
        # Large literals should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
    
    def test_no_literals_in_typescript_code(self):
        """Test processing TypeScript code without literals."""
        code = '''
interface User {
    id: number;
    name: string;
}

function processUser(user: User): void {
    console.log(user.name);
}

class UserService {
    getUser(id: number): User | null {
        return null;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_string_length=10)
        adapter._cfg = TypeScriptCfg(strip_literals=literal_config)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Code should be mostly unchanged (except possible function body stripping)
        assert "interface User {" in result
        assert "function processUser(user: User): void" in result
        assert "class UserService {" in result
        
        # No literals should be removed
        assert meta.get("code.removed.literals", 0) == 0
    
    def test_combined_literal_and_function_trimming(self):
        """Test combining literal trimming with function body stripping in TypeScript."""
        code = '''
const DATA: string[] = [
    "item1", "item2", "item3", "item4", "item5",
    "item6", "item7", "item8", "item9", "item10"
];

function processData(): string[] {
    const result: string[] = [];
    for (const item of DATA) {
        result.push(item.toUpperCase());
    }
    return result;
}
'''
        
        adapter = TypeScriptAdapter()
        literal_config = LiteralConfig(max_array_elements=5)
        adapter._cfg = TypeScriptCfg(
            strip_literals=literal_config,
            strip_function_bodies=True
        )
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Array should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        
        # Function body should be stripped
        assert "function processData(): string[]" in result
        assert ("// … body omitted" in result or "/* … body omitted" in result or 
                "// … function omitted" in result or "/* … function omitted" in result) or meta.get("code.removed.functions", 0) > 0
        assert "result.push(item.toUpperCase());" not in result or "..." in result
        
        # Both optimizations should have occurred
        if "more]" in result:
            assert meta.get("code.removed.literals", 0) > 0
        if "body omitted" in result or "function omitted" in result:
            assert meta.get("code.removed.functions", 0) > 0
