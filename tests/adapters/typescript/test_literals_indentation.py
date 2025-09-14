"""
Test literal trimming with correct indentation handling for TypeScript.
"""

from lg.adapters.typescript import TypeScriptCfg
from tests.adapters.typescript.conftest import make_adapter
from tests.conftest import lctx_ts


def test_typescript_object_literal_indentation():
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

    adapter = make_adapter(cfg)
    adapter._cfg = cfg

    context = lctx_ts(code)
    result, _ = adapter.process(context)

    # Проверяем, что отступы корректны
    lines = result.split('\n')

    # Ищем строку с placeholder'ом в smallConfig
    placeholder_line = None
    for i, line in enumerate(lines):
        if '"…": "…"' in line and 'smallConfig' in lines[i - 2] if i >= 2 else False:
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

        adapter = make_adapter(cfg)
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


    def test_typescript_object_indentation_preserved():
        """Test that TypeScript object trimming preserves correct indentation."""
        code = '''
    export class LiteralDataManager {
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
    }
    '''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 40  # Force trimming of large object
        adapter = make_adapter(cfg)

        lctx = lctx_ts(code)
        result, meta = adapter.process(lctx)

        lines = result.split('\n')

        # Find the large config object
        large_config_start = None
        large_config_end = None
        for i, line in enumerate(lines):
            if "private readonly largeConfig = {" in line:
                large_config_start = i
            if large_config_start is not None and "};" in line and "literal object" in line:
                large_config_end = i
                break

        assert large_config_start is not None, "Large config start not found"
        assert large_config_end is not None, "Large config end not found"

        # Check that object properties have correct indentation (8 spaces)
        for i in range(large_config_start + 1, large_config_end):
            line = lines[i]
            if line.strip() and '"' in line and ':' in line:  # Line with object properties
                # Should start with 8 spaces (4 for class + 4 for object content)
                assert line.startswith('        '), f"Incorrect indentation on line {i}: '{line}'"

        # Check that closing brace has correct indentation (4 spaces)
        closing_line = lines[large_config_end]
        assert closing_line.strip().startswith('}'), f"Closing brace not found on line {large_config_end}"
        # The line should start with 4 spaces before the }
        brace_position = closing_line.find('}')
        indent_before_brace = closing_line[:brace_position]
        assert indent_before_brace == '    ', f"Incorrect closing brace indentation: '{indent_before_brace}'"


    def test_typescript_array_indentation_preserved():
        """Test that TypeScript array trimming preserves correct indentation."""
        code = '''
    function processData(): void {
        const largeArray = [
            "item_001", "item_002", "item_003", "item_004", "item_005",
            "item_006", "item_007", "item_008", "item_009", "item_010",
            "item_011", "item_012", "item_013", "item_014", "item_015",
            "item_016", "item_017", "item_018", "item_019", "item_020",
            "item_021", "item_022", "item_023", "item_024", "item_025"
        ];
        
        return largeArray;
    }
    '''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 30  # Force trimming
        adapter = make_adapter(cfg)

        lctx = lctx_ts(code)
        result, meta = adapter.process(lctx)

        lines = result.split('\n')

        # Find the array declaration
        array_start = None
        array_end = None
        for i, line in enumerate(lines):
            if "const largeArray = [" in line:
                array_start = i
            if array_start is not None and "];" in line and "literal array" in line:
                array_end = i
                break

        assert array_start is not None, "Array start not found"
        assert array_end is not None, "Array end not found"

        # Check that array elements have correct indentation (8 spaces)
        for i in range(array_start + 1, array_end):
            line = lines[i]
            if line.strip() and '"' in line:  # Line with array elements
                # Should start with 8 spaces (4 for function + 4 for array content)
                assert line.startswith('        '), f"Incorrect indentation on line {i}: '{line}'"

        # Check that closing bracket has correct indentation (4 spaces)
        closing_line = lines[array_end]
        assert closing_line.strip().startswith(']'), f"Closing bracket not found on line {array_end}"
        # The line should start with 4 spaces before the ]
        bracket_position = closing_line.find(']')
        indent_before_bracket = closing_line[:bracket_position]
        assert indent_before_bracket == '    ', f"Incorrect closing bracket indentation: '{indent_before_bracket}'"


    def test_typescript_module_level_constants():
        """Test that module-level constants maintain correct indentation."""
        code = '''
    export const LARGE_CONSTANTS = {
        HTTP_STATUS_CODES: {
            CONTINUE: 100,
            SWITCHING_PROTOCOLS: 101,
            OK: 200,
            CREATED: 201,
            ACCEPTED: 202,
            NON_AUTHORITATIVE_INFORMATION: 203,
            NO_CONTENT: 204,
            RESET_CONTENT: 205,
            PARTIAL_CONTENT: 206
        },
        ERROR_MESSAGES: {
            VALIDATION_FAILED: "Input validation failed. Please check your data and try again.",
            AUTHENTICATION_REQUIRED: "Authentication is required to access this resource.",
            AUTHORIZATION_FAILED: "You do not have permission to perform this action."
        }
    };
    '''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 35  # Force trimming
        adapter = make_adapter(cfg)

        lctx = lctx_ts(code)
        result, meta = adapter.process(lctx)

        lines = result.split('\n')

        # Find the constants object
        constants_start = None
        constants_end = None
        for i, line in enumerate(lines):
            if "export const LARGE_CONSTANTS = {" in line:
                constants_start = i
            if constants_start is not None and "};" in line and "literal object" in line:
                constants_end = i
                break

        assert constants_start is not None, "Constants start not found"
        assert constants_end is not None, "Constants end not found"

        # Check that object properties have correct indentation (4 spaces for top-level content)
        for i in range(constants_start + 1, constants_end):
            line = lines[i]
            if line.strip() and '"' in line and ':' in line:  # Line with object properties
                # Should start with 4 spaces (top-level object content)
                assert line.startswith('    '), f"Incorrect indentation on line {i}: '{line}'"

        # Check that closing brace has no indentation (top-level)
        closing_line = lines[constants_end]
        assert closing_line.strip().startswith('}'), f"Closing brace not found on line {constants_end}"
        # The line should start with no spaces before the }
        brace_position = closing_line.find('}')
        indent_before_brace = closing_line[:brace_position]
        assert indent_before_brace == '', f"Incorrect closing brace indentation: '{indent_before_brace}'"


    def test_typescript_nested_object_indentation():
        """Test deeply nested objects maintain correct indentation at all levels."""
        code = '''
    class ConfigManager {
        public getConfig() {
            const nestedData = {
                level1: {
                    level2: {
                        level3: {
                            data: [
                                { id: 1, name: "First", active: true },
                                { id: 2, name: "Second", active: false },
                                { id: 3, name: "Third", active: true }
                            ],
                            metadata: {
                                created: "2024-01-01",
                                updated: "2024-01-15",
                                version: 3,
                                checksum: "abcdef123456"
                            }
                        }
                    }
                }
            };
            return nestedData;
        }
    }
    '''

        cfg = TypeScriptCfg()
        cfg.literals.max_tokens = 50  # Force trimming of the large nested structure
        adapter = make_adapter(cfg)

        lctx = lctx_ts(code)
        result, meta = adapter.process(lctx)

        # The nested object should be trimmed but maintain proper indentation
        lines = result.split('\n')

        # Find the nested object
        nested_start = None
        nested_end = None
        for i, line in enumerate(lines):
            if "const nestedData = {" in line:
                nested_start = i
            if nested_start is not None and "};" in line and "literal object" in line:
                nested_end = i
                break

        assert nested_start is not None, "Nested object start not found"
        assert nested_end is not None, "Nested object end not found"

        # Check that the object content has proper indentation (12 spaces: 4 class + 4 method + 4 object)
        for i in range(nested_start + 1, nested_end):
            line = lines[i]
            if line.strip() and '"' in line and ':' in line:  # Line with object properties
                # Should start with 12 spaces
                assert line.startswith('            '), f"Incorrect indentation on line {i}: '{line}'"

        # Check that closing brace has correct indentation (8 spaces: 4 class + 4 method)
        closing_line = lines[nested_end]
        assert closing_line.strip().startswith('}'), f"Closing brace not found on line {nested_end}"
        brace_position = closing_line.find('}')
        indent_before_brace = closing_line[:brace_position]
        assert indent_before_brace == '        ', f"Incorrect closing brace indentation: '{indent_before_brace}'"
