"""
Tests for public API filtering in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FunctionBodyConfig
from .conftest import create_typescript_context


class TestTypeScriptPublicAPIFiltering:
    """Test public API filtering for TypeScript code."""
    
    def test_public_api_only_with_access_modifiers(self):
        """Test public API filtering with TypeScript access modifiers."""
        code = '''export class UserService {
    public getName(): string {
        return this.name;
    }
    
    private validateUser(user: any): boolean {
        return user.id > 0;
    }
    
    protected processUser(user: any): void {
        this.validateUser(user);
    }
    
    getUsers(): Promise<User[]> {
        // No modifier = public by default
        return this.fetchUsers();
    }
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Public methods should be preserved
        assert "public getName():" in result
        assert "getUsers():" in result  # No modifier = public
        
        # Private/protected methods should be removed
        assert "private validateUser" not in result
        assert "protected processUser" not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
    
    def test_exported_elements_are_public(self):
        """Test that exported elements are considered public."""
        code = '''class InternalClass {
    method() {
        return "internal";
    }
}

export class PublicClass {
    method() {
        return "public";
    }
}

export function exportedFunction() {
    return "exported";
}

function internalFunction() {
    return "internal";
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Exported elements should be preserved
        assert "export class PublicClass" in result
        assert "export function exportedFunction" in result
        
        # Non-exported elements should be removed
        assert "class InternalClass" not in result
        assert "function internalFunction" not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
    
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


class TestTypeScriptPublicAPIEdgeCases:
    """Test edge cases for TypeScript public API filtering."""
    
    def test_empty_interface(self):
        """Test handling of empty interfaces."""
        code = '''export interface EmptyInterface {
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Empty public interface should be preserved
        assert "export interface EmptyInterface {" in result
    
    def test_mixed_visibility_class(self):
        """Test class with mixed public/private methods."""
        code = '''export class MixedClass {
    public publicMethod(): string {
        return "public";
    }
    
    private privateMethod(): string {
        return "private";
    }
    
    get publicProperty(): string {
        return this._value;
    }
    
    private get privateProperty(): string {
        return this._internal;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Public elements should be preserved
        assert "public publicMethod():" in result
        assert "get publicProperty():" in result
        
        # Private elements should be removed
        assert "private privateMethod():" not in result
        assert "private get privateProperty():" not in result
    
    def test_no_functions_or_classes(self):
        """Test TypeScript file with no functions or classes."""
        code = '''// Just some constants
export const PI = 3.14159;
export const MAX_SIZE = 1000;

// And some type definitions
export type User = {
    id: number;
    name: string;
};
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Should be preserved since there are no private elements to filter
        assert "export const PI = 3.14159;" in result
        assert "export type User = {" in result
        assert meta.get("code.removed.private_elements", 0) == 0
    
    def test_interface_and_type_preservation(self):
        """Test that interfaces and types are preserved when exported."""
        code = '''interface InternalInterface {
    id: number;
}

export interface PublicInterface {
    name: string;
}

type InternalType = {
    data: string;
};

export type PublicType = {
    value: number;
};
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(public_api_only=True)
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Exported types should be preserved
        assert "export interface PublicInterface {" in result
        assert "export type PublicType = {" in result
        
        # Non-exported types should be removed
        assert "interface InternalInterface {" not in result
        assert "type InternalType = {" not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
    
    def test_combined_public_api_and_comment_filtering(self):
        """Test combining public API filtering with comment processing."""
        code = '''export function publicFunction(): string {
    // Public function comment
    return "public";
}

function privateFunction(): string {
    // Private function comment
    return "private";
}
'''
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(
            public_api_only=True,
            comment_policy="keep_all"
        )
        
        result, meta = adapter.process(create_typescript_context(code))
        
        # Public function and its comment should be preserved
        assert "export function publicFunction():" in result
        assert "// Public function comment" in result
        
        # Private function should be removed entirely
        assert "function privateFunction():" not in result
        assert "// Private function comment" not in result
        
        assert meta.get("code.removed.private_elements", 0) > 0
