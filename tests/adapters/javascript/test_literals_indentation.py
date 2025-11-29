"""
Test literal trimming with correct indentation handling for JavaScript.
"""

from lg.adapters.javascript import JavaScriptCfg
from .utils import lctx, make_adapter

def test_javascript_object_literal_indentation():
    """Test indentation in JavaScript objects."""
    code = '''export class LiteralDataManager {
    // Class properties with various literal types
    #smallConfig = {
        debug: true,
        version: "1.0.0"
    };

    #largeConfig = {
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

    cfg = JavaScriptCfg()
    cfg.literals.max_tokens = 10  # Very small limit to force trimming

    adapter = make_adapter(cfg)

    context = lctx(code)
    result, _ = adapter.process(context)

    # Check that indentation is correct
    lines = result.split('\n')

    # Look for line with placeholder in largeConfig
    placeholder_line = None
    for i, line in enumerate(lines):
        if '"…"' in line:
            # Check context - should be inside largeConfig
            if i > 5:  # Skip initial lines
                placeholder_line = i
                break

    if placeholder_line is not None:
        # Check placeholder indentation
        placeholder_indent = ""
        for char in lines[placeholder_line]:
            if char in ' \t':
                placeholder_indent += char
            else:
                break

        # Check that indentation is not empty
        assert len(placeholder_indent) > 0, f"Placeholder should have indentation"


def test_javascript_array_indentation_preserved():
    """Test that JavaScript array trimming preserves correct indentation."""
    code = '''
export class LiteralDataManager {
    constructor() {
        this.supportedLanguages = [
            "english", "spanish", "french", "german", "italian", "portuguese",
            "russian", "chinese", "japanese", "korean", "arabic", "hindi",
            "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
            "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
        ];
    }
}
'''

    cfg = JavaScriptCfg()
    cfg.literals.max_tokens = 30  # Force trimming
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    lines = result.split('\n')

    # Find the array declaration
    array_start = None
    for i, line in enumerate(lines):
        if "this.supportedLanguages = [" in line:
            array_start = i
            break

    if array_start is not None:
        # Check that array elements have proper indentation
        for i in range(array_start + 1, min(array_start + 10, len(lines))):
            line = lines[i]
            if line.strip() and '"' in line and not '];' in line:  # Line with array elements
                # Should have some indentation
                indent_before_content = len(line) - len(line.lstrip())
                assert indent_before_content > 0, f"Array element should be indented on line {i}"


def test_javascript_module_level_constants():
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

    cfg = JavaScriptCfg()
    cfg.literals.max_tokens = 35  # Force trimming
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    lines = result.split('\n')

    # Find the constants object
    constants_start = None
    for i, line in enumerate(lines):
        if "export const LARGE_CONSTANTS = {" in line:
            constants_start = i
            break

    if constants_start is not None:
        # Check that object properties have correct indentation
        for i in range(constants_start + 1, min(constants_start + 15, len(lines))):
            line = lines[i]
            if line.strip() and ':' in line and not line.strip().startswith('//'):
                # Should start with 4 spaces (top-level object content)
                if not line.startswith('};'):
                    indent_before_content = len(line) - len(line.lstrip())
                    assert indent_before_content >= 4, f"Incorrect indentation on line {i}: '{line}'"


def test_javascript_nested_object_indentation():
    """Test deeply nested objects maintain correct indentation at all levels."""
    code = '''
class ConfigManager {
    getConfig() {
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

    cfg = JavaScriptCfg()
    cfg.literals.max_tokens = 50  # Force trimming of the large nested structure
    adapter = make_adapter(cfg)

    result, meta = adapter.process(lctx(code))

    # The nested object should be trimmed but maintain proper indentation
    lines = result.split('\n')

    # Find the nested object
    nested_start = None
    for i, line in enumerate(lines):
        if "const nestedData = {" in line:
            nested_start = i
            break

    if nested_start is not None:
        # Check that the object content has proper indentation
        for i in range(nested_start + 1, min(nested_start + 15, len(lines))):
            line = lines[i]
            if line.strip() and ':' in line and not line.strip().startswith('//'):
                # Should have indentation (at least 12 spaces: 4 class + 4 method + 4 object)
                indent_before_content = len(line) - len(line.lstrip())
                assert indent_before_content >= 8, f"Incorrect indentation on line {i}: '{line}'"


def test_javascript_return_object_indentation():
    """Test indentation in JavaScript return objects."""
    code = '''
function processData() {
    const smallArray = ["one", "two", "three"];

    const largeArray = [
        "item_001", "item_002", "item_003", "item_004", "item_005",
        "item_006", "item_007", "item_008", "item_009", "item_010",
        "item_011", "item_012", "item_013", "item_014", "item_015"
    ];

    return {
        tags: smallArray,
        items: largeArray,
        metadata: { type: "test", count: smallArray.length }
    };
}
'''

    cfg = JavaScriptCfg()
    cfg.literals.max_tokens = 10  # Very small limit to force trimming

    adapter = make_adapter(cfg)

    context = lctx(code)
    result, _ = adapter.process(context)

    # Check that indentation is correct
    lines = result.split('\n')

    # Look for line with placeholder in return object
    return_line = None
    for i, line in enumerate(lines):
        if 'return {' in line:
            return_line = i
            break

    if return_line is not None:
        # Check that properties in return object have proper indentation
        for i in range(return_line + 1, min(return_line + 10, len(lines))):
            line = lines[i]
            if line.strip() and ':' in line and not '};' in line:
                # Should have indentation (8 spaces: 4 for function + 4 for object)
                indent_before_content = len(line) - len(line.lstrip())
                assert indent_before_content >= 4, f"Incorrect indentation on line {i}: '{line}'"
