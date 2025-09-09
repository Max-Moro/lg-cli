"""
Тестирование универсальной логики классификации функций и методов.
Проверяем, что новые утилитарные функции правильно работают для разных языков.
"""

from pathlib import Path
from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.context import LightweightContext


def lctx(raw_text: str, filename: str) -> LightweightContext:
    """Создает LightweightContext для тестов."""
    return LightweightContext(
        file_path=Path(filename),
        raw_text=raw_text,
        group_size=1,
        mixed=False
    )


def test_python_public_api_classification():
    """Проверяем, что Python адаптер правильно классифицирует функции и методы."""
    
    python_code = '''
def public_function():
    """Public function."""
    return "public"

def _private_function():
    """Private function.""" 
    return "private"

class TestClass:
    def public_method(self):
        """Public method."""
        return "public method"
    
    def _private_method(self):
        """Private method."""
        return "private method"
    
    @staticmethod
    def static_method():
        """Static method."""
        return "static"
'''
    
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(public_api_only=True)
    
    result, meta = adapter.process(lctx(python_code, "test.py"))
    
    print("=== Python Public API Test ===")
    print(f"Functions removed: {meta.get('code.removed.functions', 0)}")
    print(f"Methods removed: {meta.get('code.removed.methods', 0)}")
    print()
    
    # Проверяем, что публичные элементы сохранены
    assert "def public_function():" in result
    assert "def public_method(self):" in result
    assert "def static_method():" in result
    
    # Проверяем, что приватные элементы удалены
    assert "def _private_function():" not in result
    assert "def _private_method(self):" not in result
    
    print("✓ Python public API classification works correctly")


def test_typescript_public_api_classification():
    """Проверяем, что TypeScript адаптер правильно классифицирует функции и методы."""
    
    typescript_code = '''
export function publicFunction(): string {
    return "public";
}

function privateFunction(): string {
    return "private";
}

export class TestClass {
    public publicMethod(): string {
        return "public method";
    }
    
    private privateMethod(): string {
        return "private method";
    }
    
    protected protectedMethod(): string {
        return "protected method";
    }
    
    static staticMethod(): string {
        return "static";
    }
}

class PrivateClass {
    method(): string {
        return "private class method";
    }
}
'''
    
    adapter = TypeScriptAdapter()
    adapter._cfg = TypeScriptCfg(public_api_only=True)
    
    result, meta = adapter.process(lctx(typescript_code, "test.ts"))
    
    print("=== TypeScript Public API Test ===")
    print(f"Functions removed: {meta.get('code.removed.functions', 0)}")
    print(f"Methods removed: {meta.get('code.removed.methods', 0)}")
    print(f"Classes removed: {meta.get('code.removed.classes', 0)}")
    print()
    
    # Проверяем, что экспортированные элементы сохранены
    assert "export function publicFunction" in result
    assert "export class TestClass" in result
    assert "public publicMethod" in result
    
    # Проверяем, что приватные элементы удалены или заменены плейсхолдерами
    assert "function privateFunction" not in result or "… function" in result
    assert "private privateMethod" not in result or "… method" in result
    assert "protected protectedMethod" not in result or "… method" in result
    assert "class PrivateClass" not in result or "… class" in result
    
    print("✓ TypeScript public API classification works correctly")


def test_python_function_body_stripping():
    """Проверяем, что удаление тел функций работает для Python."""
    
    python_code = '''
def function_with_body():
    """Function with body."""
    x = 1
    y = 2
    return x + y

class TestClass:
    def method_with_body(self):
        """Method with body."""
        self.value = 42
        return self.value
'''
    
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(strip_function_bodies=True)
    
    result, meta = adapter.process(lctx(python_code, "test.py"))
    
    print("=== Python Function Body Stripping Test ===")
    print(f"Function bodies removed: {meta.get('code.removed.function_bodies', 0)}")
    print(f"Method bodies removed: {meta.get('code.removed.method_bodies', 0)}")
    print()
    
    # Проверяем, что тела удалены
    assert "x = 1" not in result
    assert "y = 2" not in result
    assert "self.value = 42" not in result
    
    # Но сигнатуры остались
    assert "def function_with_body():" in result
    assert "def method_with_body(self):" in result
    
    print("✓ Python function body stripping works correctly")


def test_typescript_function_body_stripping():
    """Проверяем, что удаление тел функций работает для TypeScript."""
    
    typescript_code = '''
function functionWithBody(): number {
    const x = 1;
    const y = 2;
    return x + y;
}

class TestClass {
    methodWithBody(): number {
        this.value = 42;
        return this.value;
    }
}
'''
    
    adapter = TypeScriptAdapter()
    adapter._cfg = TypeScriptCfg(strip_function_bodies=True)
    
    result, meta = adapter.process(lctx(typescript_code, "test.ts"))
    
    print("=== TypeScript Function Body Stripping Test ===")
    print(f"Function bodies removed: {meta.get('code.removed.function_bodies', 0)}")
    print(f"Method bodies removed: {meta.get('code.removed.method_bodies', 0)}")
    print()
    
    # Проверяем, что тела удалены
    assert "const x = 1;" not in result
    assert "const y = 2;" not in result
    assert "this.value = 42;" not in result
    
    # Но сигнатуры остались
    assert "function functionWithBody(): number" in result
    assert "methodWithBody(): number" in result
    
    print("✓ TypeScript function body stripping works correctly")


if __name__ == "__main__":
    test_python_public_api_classification()
    test_typescript_public_api_classification()
    test_python_function_body_stripping()
    test_typescript_function_body_stripping()
    
    print("\n🎉 All tests passed! Universal function/method classification is working correctly.")
