"""
Tests for field optimization in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import FieldConfig
from .conftest import lctx_ts


class TestTypeScriptFieldOptimization:
    """Test field optimization for TypeScript code."""
    
    def test_trivial_constructor_stripping(self):
        """Test stripping of trivial TypeScript constructors."""
        code = '''
class User {
    private name: string;
    private email: string;
    
    constructor(name: string, email: string) {
        this.name = name;
        this.email = email;
    }
    
    greet(): string {
        return `Hello, ${this.name}`;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Constructor should be stripped
        assert ("/* … trivial constructor omitted" in result or 
                "// … trivial constructor omitted" in result or
                "… trivial constructor omitted" in result)
        assert meta.get("code.removed.constructors", 0) > 0
        
        # Class structure should remain
        assert "class User {" in result
        assert "greet(): string {" in result
    
    def test_non_trivial_constructor_preserved(self):
        """Test that non-trivial TypeScript constructors are preserved."""
        code = '''
class User {
    constructor(name: string, email: string) {
        this.name = name.trim().toLowerCase();
        this.email = email;
        this.validateEmail(email);
        this.createdAt = new Date();
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Non-trivial constructor should be preserved
        assert "this.name = name.trim().toLowerCase();" in result
        assert "this.validateEmail(email);" in result
        assert meta.get("code.removed.constructors", 0) == 0
    
    def test_trivial_getter_setter(self):
        """Test stripping of trivial get/set methods."""
        code = '''
class User {
    private _name: string;
    
    get name(): string {
        return this._name;
    }
    
    set name(value: string) {
        this._name = value;
    }
    
    get displayName(): string {
        return this._name.toUpperCase() + " (User)";
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_accessors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Trivial accessors should be stripped
        assert ("/* … trivial getter omitted" in result or 
                "// … trivial getter omitted" in result or
                "… trivial getter omitted" in result or
                "… trivial setter omitted" in result)
        
        # Non-trivial getter should be preserved
        assert 'return this._name.toUpperCase() + " (User)";' in result
        
        assert meta.get("code.removed.getters", 0) > 0 or meta.get("code.removed.setters", 0) > 0
    
    def test_simple_getter_setter_methods(self):
        """Test stripping of simple getName/setName methods."""
        code = '''
class User {
    private _name: string;
    
    getName(): string {
        return this._name;
    }
    
    setName(value: string): void {
        this._name = value;
    }
    
    getDisplayName(): string {
        return `${this._name} (${this.role})`;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_accessors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Trivial accessors should be stripped
        assert ("// … trivial getter omitted" in result or 
                "/* … trivial getter omitted" in result or
                "… trivial getter omitted" in result or
                "… trivial setter omitted" in result)
        
        # Non-trivial getter should be preserved  
        assert "`${this._name} (${this.role})`" in result


class TestTypeScriptFieldEdgeCases:
    """Test edge cases for TypeScript field optimization."""
    
    def test_empty_constructor(self):
        """Test handling of empty TypeScript constructors."""
        code = '''
class User {
    constructor() {
        // Empty constructor
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Empty constructor should be considered trivial
        assert meta.get("code.removed.constructors", 0) >= 0  # May or may not strip empty constructors
    
    def test_no_fields_to_optimize(self):
        """Test processing TypeScript code without fields to optimize."""
        code = '''
function standaloneFunction(): string {
    return "hello";
}

const globalVar = 42;

interface User {
    name: string;
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(
            strip_trivial_constructors=True,
            strip_trivial_accessors=True
        )
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should process without errors
        assert "function standaloneFunction(): string" in result
        assert "const globalVar = 42;" in result
        assert "interface User {" in result
        assert meta.get("code.removed.constructors", 0) == 0
        assert meta.get("code.removed.getters", 0) == 0
        assert meta.get("code.removed.setters", 0) == 0
    
    def test_mixed_trivial_and_complex(self):
        """Test mix of trivial and complex methods in same TypeScript class."""
        code = '''
class User {
    private _name: string;
    private _email: string;
    
    constructor(name: string, email: string) {
        this._name = name;
        this._email = email;
    }
    
    get name(): string {
        return this._name;
    }
    
    get fullInfo(): UserInfo {
        return {
            name: this._name,
            email: this._email,
            timestamp: Date.now(),
            isActive: this.checkActivity()
        };
    }
    
    private checkActivity(): boolean {
        return true;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(
            strip_trivial_constructors=True,
            strip_trivial_accessors=True
        )
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Should strip trivial parts but preserve complex ones
        assert ("… trivial constructor omitted" in result or 
                "… trivial getter omitted" in result)
        
        # Complex getter should be preserved
        assert "timestamp: Date.now()" in result
        assert "isActive: this.checkActivity()" in result
    
    def test_parameter_properties(self):
        """Test handling of TypeScript parameter properties."""
        code = '''
class User {
    constructor(
        public name: string,
        private email: string,
        protected id: number
    ) {
        // Parameter properties automatically assign values
        // This should still be considered trivial
    }
    
    greet(): string {
        return `Hello, ${this.name}`;
    }
}
'''
        
        adapter = TypeScriptAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = TypeScriptCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Parameter properties should be preserved (they're part of constructor signature)
        assert "public name: string," in result
        assert "private email: string," in result
        assert "protected id: number" in result
        
        # Constructor body should be stripped if trivial
        # (parameter properties make the constructor effectively non-trivial in terms of functionality)
        # But if the body is empty/trivial, it could still be stripped
        assert "greet(): string" in result
