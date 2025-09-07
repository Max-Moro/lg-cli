"""
Tests for literal trimming in TypeScript adapter.
"""

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_ts, do_literals, assert_golden_match


class TestTypeScriptLiteralOptimization:
    """Test literal trimming for TypeScript code."""
    
    def test_string_trimming_basic(self, do_literals):
        """Test basic string literal trimming."""
        literal_config = LiteralConfig(
            max_string_length=50
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Long strings should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
        assert "… string trimmed" in result or "…" in result
        
        assert_golden_match(result, "literals", "string_trimming")
    
    def test_array_element_limiting(self, do_literals):
        """Test array element limiting."""
        literal_config = LiteralConfig(
            max_array_elements=3
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Large arrays should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
        assert "… array trimmed" in result or "…" in result
        
        assert_golden_match(result, "literals", "array_limiting")
    
    def test_object_property_limiting(self, do_literals):
        """Test object property limiting."""
        literal_config = LiteralConfig(
            max_object_properties=4
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Large objects should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
        assert "… object trimmed" in result or "…" in result
        
        assert_golden_match(result, "literals", "object_limiting")
    
    def test_multiline_literal_limiting(self, do_literals):
        """Test multiline literal limiting."""
        literal_config = LiteralConfig(
            max_literal_lines=5
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Long multiline literals should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
        
        assert_golden_match(result, "literals", "multiline_limiting")
    
    def test_collapse_threshold(self, do_literals):
        """Test literal collapse threshold."""
        literal_config = LiteralConfig(
            collapse_threshold=100  # Collapse literals over 100 chars
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Large literals should be collapsed
        assert meta.get("code.removed.literal_data", 0) > 0
        
        assert_golden_match(result, "literals", "collapse_threshold")
    
    def test_combined_literal_limits(self, do_literals):
        """Test combined literal optimization limits."""
        literal_config = LiteralConfig(
            max_string_length=30,
            max_array_elements=2,
            max_object_properties=3,
            max_literal_lines=3,
            collapse_threshold=80
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(do_literals))
        
        # Multiple types of literals should be optimized
        assert meta.get("code.removed.literal_data", 0) > 0
        
        assert_golden_match(result, "literals", "combined_limits")


class TestTypeScriptLiteralEdgeCases:
    """Test edge cases for TypeScript literal optimization."""
    
    def test_template_literals(self):
        """Test template literal handling."""
        code = '''
const message = `
    This is a very long template literal
    that spans multiple lines and contains
    ${user.name} interpolated expressions
    with lots of additional content that
    should be trimmed according to policies.
`;

const shortTemplate = `Hello ${name}!`;

const complexTemplate = `
    User: ${user.name}
    Email: ${user.email}
    Status: ${user.isActive ? 'Active' : 'Inactive'}
    Last Login: ${formatDate(user.lastLogin)}
    Preferences: ${JSON.stringify(user.preferences)}
`;
'''
        
        literal_config = LiteralConfig(
            max_string_length=50,
            max_literal_lines=3
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Long template literals should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
        assert "shortTemplate" in result  # Short ones should remain
    
    def test_regex_literals(self):
        """Test regular expression literal handling."""
        code = '''
const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$/;
const phoneRegex = /^\\+?[1-9]\\d{1,14}$/;
const complexRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$/;

// Very complex regex that should be trimmed
const urlRegex = /^https?:\\/\\/(www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b([-a-zA-Z0-9()@:%_\\+.~#?&//=]*)$/;
'''
        
        literal_config = LiteralConfig(
            max_string_length=60
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Simple regexes should remain, complex ones might be trimmed
        assert "emailRegex" in result
        assert "phoneRegex" in result
    
    def test_json_data_structures(self):
        """Test JSON-like data structure handling."""
        code = '''
const apiResponse = {
    data: [
        {
            id: 1,
            name: "John Doe",
            email: "john.doe@example.com",
            address: {
                street: "123 Main St",
                city: "Anytown",
                state: "CA",
                zip: "12345"
            },
            preferences: {
                theme: "dark",
                notifications: true,
                language: "en-US"
            }
        },
        {
            id: 2,
            name: "Jane Smith",
            email: "jane.smith@example.com",
            address: {
                street: "456 Oak Ave",
                city: "Other City",
                state: "NY",
                zip: "67890"
            },
            preferences: {
                theme: "light",
                notifications: false,
                language: "es-ES"
            }
        }
    ],
    meta: {
        total: 2,
        page: 1,
        limit: 10
    }
};
'''
        
        literal_config = LiteralConfig(
            max_array_elements=1,
            max_object_properties=3
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Complex nested structures should be trimmed
        assert meta.get("code.removed.literal_data", 0) > 0
    
    def test_type_annotations_with_literals(self):
        """Test literals in type annotations and interfaces."""
        code = '''
interface Config {
    mode: "development" | "production" | "testing";
    ports: [3000, 3001, 3002, 3003, 3004];
    features: {
        authentication: boolean;
        logging: boolean;
        monitoring: boolean;
        caching: boolean;
        compression: boolean;
    };
}

const defaultConfig: Config = {
    mode: "development",
    ports: [3000, 3001, 3002, 3003, 3004],
    features: {
        authentication: true,
        logging: true,
        monitoring: false,
        caching: false,
        compression: false
    }
};

type Theme = "light" | "dark" | "auto" | "high-contrast";
type Language = "en" | "es" | "fr" | "de" | "ja" | "zh";
'''
        
        literal_config = LiteralConfig(
            max_array_elements=3,
            max_object_properties=3
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Type definitions should generally be preserved
        # but literal values might be trimmed
        assert "interface Config" in result
        assert "type Theme" in result
    
    def test_enum_definitions(self):
        """Test enum definition handling."""
        code = '''
enum Status {
    PENDING = "pending",
    PROCESSING = "processing",
    COMPLETED = "completed",
    FAILED = "failed",
    CANCELLED = "cancelled"
}

enum Priority {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4,
    EMERGENCY = 5
}

const statusMessages = {
    [Status.PENDING]: "Your request is pending approval",
    [Status.PROCESSING]: "We are processing your request",
    [Status.COMPLETED]: "Your request has been completed successfully",
    [Status.FAILED]: "Your request failed to process",
    [Status.CANCELLED]: "Your request was cancelled"
};
'''
        
        literal_config = LiteralConfig(
            max_object_properties=3,
            max_string_length=30
        )
        
        adapter = TypeScriptAdapter()
        adapter._cfg = TypeScriptCfg(literal_config=literal_config)
        
        result, meta = adapter.process(lctx_ts(code))
        
        # Enum definitions should be preserved
        # but literal values might be trimmed
        assert "enum Status" in result
        assert "enum Priority" in result
