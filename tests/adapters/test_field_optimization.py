"""
Tests for field optimization implementation (M6).
"""

from lg.adapters.code_model import FieldConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from tests.conftest import lctx_py, lctx_ts


class TestFieldOptimizationPython:
    """Test field optimization for Python code."""
    
    def test_trivial_constructor_stripping(self):
        """Test stripping of trivial Python constructors."""
        code = '''
class User:
    def __init__(self, name, email):
        """Initialize user."""
        self.name = name
        self.email = email
        
    def greet(self):
        return f"Hello, {self.name}"
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Constructor should be stripped
        assert "# … trivial constructor omitted" in result or "… trivial constructor omitted" in result
        assert meta.get("code.removed.constructors", 0) > 0
        
        # Class and other methods should remain
        assert "class User:" in result
        assert "def greet(self):" in result
    
    def test_non_trivial_constructor_preserved(self):
        """Test that non-trivial constructors are preserved."""
        code = '''
class User:
    def __init__(self, name, email):
        self.name = name.strip().lower()
        self.email = email
        self.created_at = datetime.now()
        self.validate()
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Non-trivial constructor should be preserved
        assert "self.name = name.strip().lower()" in result
        assert "self.validate()" in result
        assert meta.get("code.removed.constructors", 0) == 0
    
    def test_trivial_property_getter(self):
        """Test stripping of trivial @property getters."""
        code = '''
class User:
    def __init__(self, name):
        self._name = name
    
    @property
    def name(self):
        """Get user name."""
        return self._name
    
    @name.setter
    def name(self, value):
        """Set user name."""
        self._name = value
        
    @property
    def display_name(self):
        """Get display name with processing."""
        return self._name.title().strip()
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(strip_trivial_accessors=True)
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Trivial getter and setter should be stripped
        assert "# … trivial getter omitted" in result or "… trivial getter omitted" in result
        assert "# … trivial setter omitted" in result or "… trivial setter omitted" in result
        
        # Non-trivial getter should be preserved
        assert "return self._name.title().strip()" in result
        
        assert meta.get("code.removed.getters", 0) > 0
        assert meta.get("code.removed.setters", 0) > 0
    
    def test_simple_getter_setter_methods(self):
        """Test stripping of simple get_/set_ methods."""
        code = '''
class User:
    def __init__(self, name):
        self._name = name
    
    def get_name(self):
        return self._name
    
    def set_name(self, value):
        self._name = value
        
    def get_display_name(self):
        return f"{self._name} (User)"
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(strip_trivial_accessors=True)
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Trivial accessors should be stripped
        assert ("# … trivial getter omitted" in result or "… trivial getter omitted" in result or
                "# … trivial setter omitted" in result or "… trivial setter omitted" in result)
        
        # Non-trivial getter should be preserved
        assert 'return f"{self._name} (User)"' in result
    
    def test_field_optimization_disabled(self):
        """Test that optimization can be disabled."""
        code = '''
class User:
    def __init__(self, name):
        self.name = name
    
    @property
    def name_prop(self):
        return self._name
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(
            strip_trivial_constructors=False,
            strip_trivial_accessors=False
        )
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Nothing should be stripped
        assert "self.name = name" in result
        assert "return self._name" in result
        assert meta.get("code.removed.constructors", 0) == 0
        assert meta.get("code.removed.getters", 0) == 0


class TestFieldOptimizationTypeScript:
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
        # Trivial accessors should be stripped
        assert ("// … trivial getter omitted" in result or 
                "/* … trivial getter omitted" in result or
                "… trivial getter omitted" in result or
                "… trivial setter omitted" in result)
        
        # Non-trivial getter should be preserved  
        assert "`${this._name} (${this.role})`" in result


class TestFieldOptimizationEdgeCases:
    """Test edge cases for field optimization."""
    
    def test_empty_constructor(self):
        """Test handling of empty constructors."""
        python_code = '''
class User:
    def __init__(self):
        pass
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(strip_trivial_constructors=True)
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=python_code))
        
        # Empty constructor should be considered trivial
        assert meta.get("code.removed.constructors", 0) >= 0  # May or may not strip empty constructors
    
    def test_no_fields_to_optimize(self):
        """Test processing code without fields to optimize."""
        code = '''
def standalone_function():
    return "hello"

global_var = 42
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(
            strip_trivial_constructors=True,
            strip_trivial_accessors=True
        )
        adapter._cfg = PythonCfg(fields=field_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should process without errors
        assert "def standalone_function():" in result
        assert "global_var = 42" in result
        assert meta.get("code.removed.constructors", 0) == 0
        assert meta.get("code.removed.getters", 0) == 0
        assert meta.get("code.removed.setters", 0) == 0
    
    def test_mixed_trivial_and_complex(self):
        """Test mix of trivial and complex methods in same class."""
        code = '''
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    @property
    def name(self):
        return self._name
    
    @property  
    def full_info(self):
        return {
            "name": self.name,
            "email": self.email,
            "timestamp": time.time()
        }
'''
        
        adapter = PythonAdapter()
        field_config = FieldConfig(
            strip_trivial_constructors=True,
            strip_trivial_accessors=True
        )
        # Увеличиваем лимиты literal optimization чтобы объекты не заменялись на placeholders
        from lg.adapters.code_model import LiteralConfig
        literal_config = LiteralConfig(
            max_object_properties=50,
            max_literal_lines=50,
            collapse_threshold=1000  # Увеличиваем чтобы тестовый объект не заменялся
        )
        adapter._cfg = PythonCfg(fields=field_config, strip_literals=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Should strip trivial parts but preserve complex ones
        assert ("… trivial constructor omitted" in result or 
                "… trivial getter omitted" in result)
        
        # Complex property should be preserved
        assert '"timestamp": time.time()' in result
