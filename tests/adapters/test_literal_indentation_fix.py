"""
Тесты для проверки исправления отступов в литералах.
"""

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from tests.conftest import lctx_py, lctx_ts, stub_tokenizer


class TestLiteralIndentationFix:
    """Тесты для проверки правильности отступов в урезанных литералах."""

    def test_python_object_literal_indentation(self):
        """Тест отступов в Python объектах/словарях."""
        code = '''class DataContainer:
    def __init__(self):
        # Large dictionary (candidate for trimming)
        self.large_dict = {
            "user_id": 12345,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "12345",
                "country": "USA"
            },
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True,
                "newsletter": False
            }
        }'''

        cfg = PythonCfg()
        cfg.literals.max_tokens = 10  # Очень маленький лимит для принудительного тримминга
        
        adapter = PythonAdapter().bind(None, stub_tokenizer())
        adapter._cfg = cfg
        
        context = lctx_py(code)
        result, _ = adapter.process(context)
        
        # Проверяем, что отступы корректны
        lines = result.split('\n')
        dict_start_line = None
        for i, line in enumerate(lines):
            if 'self.large_dict = {' in line:
                dict_start_line = i
                break
        
        assert dict_start_line is not None, "Не найден словарь для тестирования"
        
        # Ищем строку с placeholder'ом
        placeholder_line = None
        for i in range(dict_start_line + 1, len(lines)):
            if '"…": "…"' in lines[i]:
                placeholder_line = i
                break
        
        assert placeholder_line is not None, "Не найден placeholder в результате"
        
        # Проверяем, что отступ placeholder'а соответствует отступам других элементов
        placeholder_indent = ""
        for char in lines[placeholder_line]:
            if char in ' \t':
                placeholder_indent += char
            else:
                break
        
        # Проверяем, что отступ не пустой (должен быть как у других элементов)
        assert len(placeholder_indent) > 0, f"Placeholder должен иметь отступ, но получили: '{lines[placeholder_line]}'"
        
        # Проверяем, что отступ соответствует отступам других элементов словаря
        expected_indent = "            "  # 12 пробелов (базовый отступ + 4 для элементов)
        assert placeholder_indent == expected_indent, f"Неправильный отступ placeholder'а: '{placeholder_indent}', ожидался: '{expected_indent}'"

    def test_typescript_object_literal_indentation(self):
        """Тест отступов в TypeScript объектах."""
        code = '''export class LiteralDataManager {
    // Class properties with various literal types
    private readonly smallConfig = {
        debug: true,
        version: "1.0.0"
    };
    
    private readonly largeConfig = {
        database: {
            host: "localhost",
            port: 5432,
            name: "application_db",
            ssl: false,
            pool: {
                min: 2,
                max: 10,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: 2000
            }
        },
        cache: {
            redis: {
                host: "localhost",
                port: 6379,
                db: 0,
                ttl: 3600
            }
        }
    };
}'''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 10  # Очень маленький лимит для принудительного тримминга
        
        adapter = TypeScriptAdapter().bind(None, stub_tokenizer())
        adapter._cfg = cfg
        
        context = lctx_ts(code)
        result, _ = adapter.process(context)
        
        # Проверяем, что отступы корректны
        lines = result.split('\n')
        
        # Ищем строку с placeholder'ом в smallConfig
        placeholder_line = None
        for i, line in enumerate(lines):
            if '"…": "…"' in line and 'smallConfig' in lines[i-2] if i >= 2 else False:
                placeholder_line = i
                break
        
        assert placeholder_line is not None, "Не найден placeholder в результате"
        
        # Проверяем отступ placeholder'а
        placeholder_indent = ""
        for char in lines[placeholder_line]:
            if char in ' \t':
                placeholder_indent += char
            else:
                break
        
        # Проверяем, что отступ не пустой
        assert len(placeholder_indent) > 0, f"Placeholder должен иметь отступ, но получили: '{lines[placeholder_line]}'"
        
        # Проверяем, что отступ соответствует отступам других элементов объекта
        expected_indent = "        "  # 8 пробелов (базовый отступ + 4 для элементов)
        assert placeholder_indent == expected_indent, f"Неправильный отступ placeholder'а: '{placeholder_indent}', ожидался: '{expected_indent}'"

    def test_typescript_return_object_indentation(self):
        """Тест отступов в TypeScript return объектах."""
        code = '''    public processData(): DataContainer {
        // Function with various literal data
        const smallArray = ["one", "two", "three"];
        
        const largeArray = [
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015"
        ];
        
        return {
            tags: smallArray,
            items: largeArray,
            metadata: { type: "test", count: smallArray.length },
            configuration: nestedData
        };
    }'''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 10  # Очень маленький лимит для принудительного тримминга
        
        adapter = TypeScriptAdapter().bind(None, stub_tokenizer())
        adapter._cfg = cfg
        
        context = lctx_ts(code)
        result, _ = adapter.process(context)
        
        # Проверяем, что отступы корректны
        lines = result.split('\n')
        
        # Ищем строку с placeholder'ом в return объекте
        placeholder_line = None
        return_line = None
        for i, line in enumerate(lines):
            if 'return {' in line:
                return_line = i
            if '"…": "…"' in line and return_line is not None and i > return_line:
                placeholder_line = i
                break
        
        assert placeholder_line is not None, "Не найден placeholder в return объекте"
        
        # Проверяем отступ placeholder'а
        placeholder_indent = ""
        for char in lines[placeholder_line]:
            if char in ' \t':
                placeholder_indent += char
            else:
                break
        
        # Проверяем, что отступ не пустой
        assert len(placeholder_indent) > 0, f"Placeholder должен иметь отступ, но получили: '{lines[placeholder_line]}'"
        
        # Проверяем, что отступ соответствует отступам других элементов объекта
        expected_indent = "            "  # 12 пробелов (базовый отступ + 8 для элементов)
        assert placeholder_indent == expected_indent, f"Неправильный отступ placeholder'а: '{placeholder_indent}', ожидался: '{expected_indent}'"
