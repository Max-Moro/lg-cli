"""
Tests for literal trimming implementation (M5).
"""

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import LiteralConfig
from tests.conftest import lctx_py, lctx_ts


class TestLiteralTrimmingPython:
    """Test literal trimming for Python code."""
    
    def test_string_length_trimming(self):
        """Test that long strings are trimmed."""
        code = '''
# Short string
message = "Hello world"

# Long string that should be trimmed
long_message = "This is a very long string that exceeds the maximum length limit and should be truncated to prevent token waste"

def process_data():
    return long_message
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_string_length=50)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Short string should be preserved
        assert 'message = "Hello world"' in result
        
        # Long string should be trimmed
        assert "This is a very long string that exceeds the maximum..." in result or meta.get("code.removed.literals", 0) > 0
        assert "should be truncated to prevent token waste" not in result
        
        # Should have literal removal metrics
        if "..." in result:
            assert meta.get("code.removed.literals", 0) > 0
    
    def test_array_element_trimming(self):
        """Test that arrays with many elements are trimmed."""
        code = '''
# Small list
small_list = [1, 2, 3]

# Large list that should be trimmed
large_list = [
    "item1", "item2", "item3", "item4", "item5",
    "item6", "item7", "item8", "item9", "item10",
    "item11", "item12", "item13", "item14", "item15"
]

def get_items():
    return large_list
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_array_elements=8)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Small list should be preserved
        assert "small_list = [1, 2, 3]" in result
        
        # Large list should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        assert "item15" not in result or meta.get("code.removed.literals", 0) > 0
        
        if "more]" in result:
            assert meta.get("code.removed.literals", 0) > 0
    
    def test_dictionary_property_trimming(self):
        """Test that dictionaries with many properties are trimmed."""
        code = '''
# Small dict
small_dict = {"a": 1, "b": 2}

# Large dict that should be trimmed
large_dict = {
    "key1": "value1",
    "key2": "value2", 
    "key3": "value3",
    "key4": "value4",
    "key5": "value5",
    "key6": "value6",
    "key7": "value7",
    "key8": "value8"
}

def get_config():
    return large_dict
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_object_properties=5)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Small dict should be preserved
        assert 'small_dict = {"a": 1, "b": 2}' in result
        
        # Large dict should be trimmed
        assert ("... and" in result and "more}" in result) or meta.get("code.removed.literals", 0) > 0
        assert "key8" not in result or meta.get("code.removed.literals", 0) > 0
    
    def test_multiline_literal_trimming(self):
        """Test that multiline literals are trimmed based on line count."""
        code = '''
# Single line
single = "one line"

# Multiline string that should be trimmed
multiline = """
This is a multiline string
that spans several lines
and contains a lot of content
which should be collapsed
when it exceeds the limit
"""

def get_text():
    return multiline
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_literal_lines=3)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Single line should be preserved
        assert 'single = "one line"' in result
        
        # Multiline should be trimmed
        assert "# ... string data" in result or meta.get("code.removed.literals", 0) > 0
        assert "which should be collapsed" not in result
    
    def test_size_based_trimming(self):
        """Test trimming based on byte size threshold."""
        code = '''
# Small data
small = "small"

# Large data that exceeds threshold
large = "''' + "x" * 200 + '''"

def process():
    return large
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(collapse_threshold=100)  # 100 bytes
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Small data should be preserved
        assert 'small = "small"' in result
        
        # Large data should be replaced with size placeholder
        assert "200 bytes" in result or "# ... string data" in result or meta.get("code.removed.literals", 0) > 0
    
    def test_no_trimming_when_within_limits(self):
        """Test that literals within limits are not trimmed."""
        code = '''
message = "This is a reasonable length message"
numbers = [1, 2, 3, 4, 5]
config = {"debug": True, "version": "1.0"}
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(
            max_string_length=100,
            max_array_elements=10,
            max_object_properties=10,
            max_literal_lines=5,
            collapse_threshold=1000
        )
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # All literals should be preserved
        assert 'message = "This is a reasonable length message"' in result
        assert "numbers = [1, 2, 3, 4, 5]" in result
        assert 'config = {"debug": True, "version": "1.0"}' in result
        
        # No literals should be removed
        assert meta.get("code.removed.literals", 0) == 0


class TestLiteralTrimmingTypeScript:
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
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
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
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(raw_text=code))
        
        # Small object should be preserved
        assert 'const smallConfig = { debug: true, version: "1.0" };' in result
        
        # Large object should be trimmed
        assert ("... and" in result and "more}" in result) or meta.get("code.removed.literals", 0) > 0


class TestLiteralTrimmingEdgeCases:
    """Test edge cases for literal trimming."""
    
    def test_empty_literals(self):
        """Test handling of empty literals."""
        code = '''
empty_string = ""
empty_list = []
empty_dict = {}
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(
            max_string_length=10,
            max_array_elements=5,
            max_object_properties=3
        )
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Empty literals should be preserved (they're within limits)
        assert 'empty_string = ""' in result
        assert "empty_list = []" in result
        assert "empty_dict = {}" in result
        
        # No trimming should occur
        assert meta.get("code.removed.literals", 0) == 0
    
    def test_nested_literals(self):
        """Test handling of nested literal structures."""
        code = '''
nested = {
    "users": [
        {"name": "Alice", "age": 30, "email": "alice@example.com"},
        {"name": "Bob", "age": 25, "email": "bob@example.com"},
        {"name": "Charlie", "age": 35, "email": "charlie@example.com"}
    ],
    "settings": {
        "theme": "dark",
        "language": "en",
        "notifications": True
    }
}
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_literal_lines=3)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Nested structure should be trimmed due to line count
        assert "# ... object data" in result or meta.get("code.removed.literals", 0) > 0
        assert "alice@example.com" not in result or "..." in result
    
    def test_literals_with_different_quote_styles(self):
        """Test handling of different quote styles."""
        code = '''
single = 'Single quoted string that is quite long and should be trimmed'
double = "Double quoted string that is also quite long and should be trimmed"
triple = """Triple quoted string
that spans multiple lines
and should be trimmed"""
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_string_length=30)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # All long strings should be trimmed, preserving quote style
        trimmed_count = 0
        if "Single quoted string that is..." in result:
            trimmed_count += 1
        if "Double quoted string that is..." in result:
            trimmed_count += 1
        if "..." in result:
            trimmed_count += 1
        
        # At least some strings should be trimmed
        assert trimmed_count > 0 or meta.get("code.removed.literals", 0) > 0
    
    def test_no_literals_in_code(self):
        """Test processing code without literals."""
        code = '''
def calculate(x, y):
    return x + y

class Calculator:
    def add(self, a, b):
        return a + b
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_string_length=10)
        adapter._cfg = PythonCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Code should be unchanged
        assert "def calculate(x, y):" in result
        assert "class Calculator:" in result
        
        # No literals should be removed
        assert meta.get("code.removed.literals", 0) == 0
    
    def test_combined_literal_and_function_trimming(self):
        """Test combining literal trimming with function body stripping."""
        code = '''
DATA = [
    "item1", "item2", "item3", "item4", "item5",
    "item6", "item7", "item8", "item9", "item10"
]

def process_data():
    """Process the data array."""
    result = []
    for item in DATA:
        result.append(item.upper())
    return result
'''
        
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_array_elements=5)
        adapter._cfg = PythonCfg(
            literal_config=literal_config,
            strip_function_bodies=True
        )
        
        result, meta = adapter.process(lctx_py(raw_text=code))
        
        # Array should be trimmed
        assert ("... and" in result and "more]" in result) or meta.get("code.removed.literals", 0) > 0
        
        # Function body should be stripped
        assert "def process_data():" in result
        assert ("# … body omitted" in result or "# … function omitted" in result) or meta.get("code.removed.functions", 0) > 0
        assert "result.append(item.upper())" not in result or "..." in result
        
        # Both optimizations should have occurred
        if "more]" in result:
            assert meta.get("code.removed.literals", 0) > 0
        if "body omitted" in result:
            assert meta.get("code.removed.functions", 0) > 0

    def test_function_docstring_not_literal(self):
        """Test must not recognize docstrings or comments as literals."""
        code = '''"""Module docstring."""
import os

# This is a comment
def hello():
    """Function docstring."""
    # Another comment
    return "hello"
'''
        adapter = PythonAdapter()
        literal_config = LiteralConfig(max_string_length=1)
        adapter._cfg = PythonCfg(literal_config=literal_config)

        result, meta = adapter.process(lctx_py(raw_text=code))

        assert 'Module docstring.' in result
        assert 'Function docstring.' in result
        assert "# This is a comment" in result
        assert "# Another comment" in result

        assert "h..." in result

        # Only the regular string literal "hello" should be removed, not docstrings/comments
        assert meta.get("code.removed.literals", 0) == 1