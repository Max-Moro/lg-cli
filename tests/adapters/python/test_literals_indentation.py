"""
Test literal trimming with correct indentation handling.
"""

from lg.adapters.python import PythonCfg
from tests.adapters.python.conftest import make_adapter
from tests.infrastructure import lctx_py


def test_python_object_literal_indentation():
    """Test indentation in Python objects/dictionaries."""
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
    cfg.literals.max_tokens = 10  # Very small limit for forced trimming

    adapter = make_adapter(cfg)

    context = lctx_py(code)
    result, _ = adapter.process(context)

    # Check that indentation is correct
    lines = result.split('\n')
    dict_start_line = None
    for i, line in enumerate(lines):
        if 'self.large_dict = {' in line:
            dict_start_line = i
            break

    assert dict_start_line is not None, "Dictionary for testing not found"

    # Look for line with placeholder
    placeholder_line = None
    for i in range(dict_start_line + 1, len(lines)):
        if '"…": "…"' in lines[i]:
            placeholder_line = i
            break

    assert placeholder_line is not None, "Placeholder not found in result"

    # Check that placeholder indentation matches other elements
    placeholder_indent = ""
    for char in lines[placeholder_line]:
        if char in ' \t':
            placeholder_indent += char
        else:
            break

    # Check that indentation is not empty (should match other elements)
    assert len(placeholder_indent) > 0, f"Placeholder should have indentation, but got: '{lines[placeholder_line]}'"

    # Check that indentation matches other dictionary elements
    expected_indent = "            "  # 12 spaces (base + 4 for elements)
    assert placeholder_indent == expected_indent, f"Wrong placeholder indentation: '{placeholder_indent}', expected: '{expected_indent}'"


def test_array_indentation_preserved():
    """Test that array trimming preserves correct indentation."""
    code = '''
class DataContainer:
    def __init__(self):
        # Large array (candidate for trimming)
        self.large_list = [
            "item_1", "item_2", "item_3", "item_4", "item_5",
            "item_6", "item_7", "item_8", "item_9", "item_10",
            "item_11", "item_12", "item_13", "item_14", "item_15",
            "item_16", "item_17", "item_18", "item_19", "item_20",
            "item_21", "item_22", "item_23", "item_24", "item_25"
        ]
'''

    cfg = PythonCfg()
    cfg.literals.max_tokens = 30  # Force trimming
    adapter = make_adapter(cfg)

    lctx = lctx_py(code)
    result, meta = adapter.process(lctx)

    # Check that indentation is preserved correctly
    lines = result.split('\n')

    # Find the array declaration lines
    array_start_line = None
    array_end_line = None
    for i, line in enumerate(lines):
        if "self.large_list = [" in line:
            array_start_line = i
        if array_start_line is not None and "]" in line and "literal array" in line:
            array_end_line = i
            break

    assert array_start_line is not None, "Array start not found"
    assert array_end_line is not None, "Array end not found"

    # Check that array elements have correct indentation (12 spaces)
    for i in range(array_start_line + 1, array_end_line):
        line = lines[i]
        if line.strip() and '"' in line:  # Line with array elements
            # Should start with 12 spaces (8 for class method + 4 for array content)
            assert line.startswith('            '), f"Incorrect indentation on line {i}: '{line}'"

    # Check that closing bracket has correct indentation (8 spaces)
    closing_line = lines[array_end_line]
    assert closing_line.strip().startswith(']'), f"Closing bracket not found on line {array_end_line}"
    # The line should start with 8 spaces before the ]
    bracket_position = closing_line.find(']')
    indent_before_bracket = closing_line[:bracket_position]
    assert indent_before_bracket == '        ', f"Incorrect closing bracket indentation: '{indent_before_bracket}'"


def test_object_indentation_preserved():
    """Test that object trimming preserves correct indentation."""
    code = '''
def process_data():
    # Nested data structure
    config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "myapp",
            "credentials": {
                "username": "admin",
                "password": "super_secret_password_123456789"
            }
        },
        "api": {
            "endpoints": ["/api/v1/users", "/api/v1/posts"],
            "rate_limit": 1000,
            "timeout": 30
        }
    }
'''

    cfg = PythonCfg()
    cfg.literals.max_tokens = 40  # Force trimming
    adapter = make_adapter(cfg)

    lctx = lctx_py(code)
    result, meta = adapter.process(lctx)

    # Check that indentation is preserved correctly
    lines = result.split('\n')

    # Find the object declaration lines
    object_start_line = None
    object_end_line = None
    for i, line in enumerate(lines):
        if "config = {" in line:
            object_start_line = i
        if object_start_line is not None and "}" in line and "literal object" in line:
            object_end_line = i
            break

    assert object_start_line is not None, "Object start not found"
    assert object_end_line is not None, "Object end not found"

    # Check that object properties have correct indentation (8 spaces)
    for i in range(object_start_line + 1, object_end_line):
        line = lines[i]
        if line.strip() and '"' in line and ':' in line:  # Line with object properties
            # Should start with 8 spaces (4 for function + 4 for object content)
            assert line.startswith('        '), f"Incorrect indentation on line {i}: '{line}'"

    # Check that closing brace has correct indentation (4 spaces)
    closing_line = lines[object_end_line]
    assert closing_line.strip().startswith('}'), f"Closing brace not found on line {object_end_line}"
    # The line should start with 4 spaces before the }
    brace_position = closing_line.find('}')
    indent_before_brace = closing_line[:brace_position]
    assert indent_before_brace == '    ', f"Incorrect closing brace indentation: '{indent_before_brace}'"


def test_top_level_object_indentation():
    """Test that top-level objects maintain correct indentation."""
    code = '''
# Module-level data
LARGE_CONFIG = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "credentials": {
            "username": "admin",
            "password": "super_secret_password_that_is_very_long_123456789"
        }
    },
    "cache": {
        "redis_host": "localhost",
        "redis_port": 6379,
        "ttl": 3600
    }
}
'''

    cfg = PythonCfg()
    cfg.literals.max_tokens = 25  # Force trimming
    adapter = make_adapter(cfg)

    lctx = lctx_py(code)
    result, meta = adapter.process(lctx)

    # Check that indentation is preserved correctly
    lines = result.split('\n')

    # Find the object declaration lines
    object_start_line = None
    object_end_line = None
    for i, line in enumerate(lines):
        if "LARGE_CONFIG = {" in line:
            object_start_line = i
        if object_start_line is not None and "}" in line and "literal object" in line:
            object_end_line = i
            break

    assert object_start_line is not None, "Object start not found"
    assert object_end_line is not None, "Object end not found"

    # Check that object properties have correct indentation (4 spaces)
    for i in range(object_start_line + 1, object_end_line):
        line = lines[i]
        if line.strip() and '"' in line and ':' in line:  # Line with object properties
            # Should start with 4 spaces (top-level indentation)
            assert line.startswith('    '), f"Incorrect indentation on line {i}: '{line}'"

    # Check that closing brace has no indentation (top-level)
    closing_line = lines[object_end_line]
    assert closing_line.strip().startswith('}'), f"Closing brace not found on line {object_end_line}"
    # The line should start with no spaces before the }
    brace_position = closing_line.find('}')
    indent_before_brace = closing_line[:brace_position]
    assert indent_before_brace == '', f"Incorrect closing brace indentation: '{indent_before_brace}'"


def test_single_line_literal_unchanged():
    """Test that single-line literals are not affected by indentation logic."""
    code = '''
def simple_data():
    small_list = [1, 2, 3]
    small_dict = {"name": "test", "value": 42}
    return small_list, small_dict
'''

    cfg = PythonCfg()
    cfg.literals.max_tokens = 100  # Don't force trimming
    adapter = make_adapter(cfg)

    lctx = lctx_py(code)
    result, meta = adapter.process(lctx)

    # Single-line literals should remain unchanged
    assert "small_list = [1, 2, 3]" in result
    assert '{"name": "test", "value": 42}' in result
    assert "literal" not in result  # No trimming comments
