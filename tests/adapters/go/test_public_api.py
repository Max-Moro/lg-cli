"""
Tests for public API filtering in Go adapter.
"""

from lg.adapters.go import GoCfg
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestGoPublicApiOptimization:
    """Test public API filtering for Go code."""

    def test_public_api_only_basic(self, do_public_api):
        """Test basic public API filtering."""
        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(do_public_api))

        assert meta.get("go.removed.function", 0) > 0

        assert "func NewUserManager" in result
        assert "func (m *UserManager) CreateUser" in result

        assert "func validateUserData" not in result
        assert "func generateID" not in result

        assert_golden_match(result, "public_api", "basic", language="go")

    def test_exported_vs_unexported(self):
        """Test distinction between exported and unexported identifiers."""
        code = '''package main

// Exported function
func PublicFunction(x int) int {
    return helper(x)
}

// Unexported function
func helper(x int) int {
    return x * 2
}

// Exported struct
type User struct {
    ID   int
    Name string
}

// Unexported struct
type internalData struct {
    secret string
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "func PublicFunction(x int) int" in result
        assert "type User struct" in result

        assert "func helper" not in result
        assert "type internalData" not in result

    def test_exported_methods(self):
        """Test filtering of exported vs unexported methods."""
        code = '''package main

type Service struct {
    cache map[string]interface{}
}

// Exported method
func (s *Service) GetValue(key string) (interface{}, bool) {
    val, ok := s.cache[key]
    return val, ok
}

// Unexported method
func (s *Service) invalidate() {
    s.cache = make(map[string]interface{})
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "func (s *Service) GetValue" in result
        assert "func (s *Service) invalidate" not in result

    def test_interface_methods(self):
        """Test that interface definitions are preserved."""
        code = '''package main

// Exported interface
type Reader interface {
    Read(p []byte) (n int, err error)
    Close() error
}

// Unexported interface
type writer interface {
    Write(p []byte) (n int, err error)
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "type Reader interface" in result
        assert "Read(p []byte) (n int, err error)" in result

        assert "type writer interface" not in result

    def test_struct_fields_visibility(self):
        """Test filtering of struct fields by visibility."""
        code = '''package main

type Config struct {
    // Exported fields
    Timeout int
    Retries int

    // Unexported fields
    debug   bool
    verbose bool
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "Timeout int" in result
        assert "Retries int" in result

    def test_package_level_variables(self):
        """Test filtering of package-level variables."""
        code = '''package main

// Exported variable
var PublicVersion = "1.0.0"

// Unexported variable
var privateSecret = "internal-use-only"

// Exported constant
const APIEndpoint = "https://api.example.com"

// Unexported constant
const internalFlag = true
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "var PublicVersion" in result
        assert "const APIEndpoint" in result

        assert "var privateSecret" not in result
        assert "const internalFlag" not in result


class TestGoPublicApiEdgeCases:
    """Test edge cases for Go public API filtering."""

    def test_type_aliases(self):
        """Test handling of type aliases."""
        code = '''package main

// Exported type alias
type UserID = int

// Unexported type alias
type internalID = string
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "type UserID = int" in result
        assert "type internalID" not in result

    def test_embedded_structs(self):
        """Test handling of embedded structs."""
        code = '''package main

type Base struct {
    ID int
}

type Extended struct {
    Base
    Name string
}

type internal struct {
    data string
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "type Base struct" in result
        assert "type Extended struct" in result
        assert "Base" in result

        assert "type internal struct" not in result

    def test_function_with_unexported_params(self):
        """Test exported functions with unexported parameter/return types."""
        code = '''package main

type internalData struct {
    value string
}

// Exported function but uses unexported type
func ProcessData(data internalData) internalData {
    return data
}
'''

        adapter = make_adapter(GoCfg(public_api_only=True))

        result, meta = adapter.process(lctx(code))

        assert "func ProcessData" in result
