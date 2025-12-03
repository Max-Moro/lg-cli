// Go module for testing literal optimization.
package main

import (
	"fmt"
)

// Short string literal (should be preserved)
const ShortMessage = "Hello, World!"

// Long string literal (candidate for trimming)
const LongMessage = "This is an extremely long message that contains a…" // literal string (−62 tokens)

// Multi-line string with formatting
const TemplateWithData = `User Information:
-…` // literal string (−45 tokens)

// DataContainer holds various literal types
type DataContainer struct {
	// Small slice (should be preserved)
	Tags []string

	// Large slice (candidate for trimming)
	Items []string

	// Small map (should be preserved)
	Metadata map[string]interface{}

	// Large map (candidate for trimming)
	Configuration map[string]interface{}
}

// LiteralDataManager manages literal data
type LiteralDataManager struct {
	// Small config (should be preserved)
	smallConfig map[string]interface{}

	// Large config (candidate for trimming)
	largeConfig map[string]interface{}

	// Supported languages
	supportedLanguages []string

	// Allowed extensions
	allowedExtensions []string
}

// NewLiteralDataManager creates a new manager instance
func NewLiteralDataManager() *LiteralDataManager {
	return &LiteralDataManager{
		smallConfig: map[string]interface{}{"…": "…"},
		largeConfig: map[string]interface{}{"…": "…"},
		supportedLanguages: []string{"…"},
		allowedExtensions: []string{"…"},
	} // literal array (−569 tokens)
}

// ProcessData creates a data container with various literals
func (m *LiteralDataManager) ProcessData() *DataContainer {
	smallSlice := []string{"one", "two", /* … */}

	largeSlice := []string{
		"item_001",
		// …
	} // literal array (−150 tokens)

	nestedData := map[string]interface{}{"…"} // literal array (−205 tokens)

	return &DataContainer{
		Tags: smallSlice,
		Items: "…",
		Metadata: map[string]interface{}{"…": "…"},
		Configuration: "…",
	} // literal array (−11 tokens)
}

// GetLongQuery returns a very long SQL-like query string
func (m *LiteralDataManager) GetLongQuery() string {
	return `
		SELECT
			users.id, users.us…` // literal string (−182 tokens)
}

// Module-level constants with different sizes
var SmallConstants = struct {
	APIVersion   string
	DefaultLimit int
}{
	APIVersion: "v1",
	DefaultLimit: 0,
} // literal array (−1 tokens)

var HTTPStatusCodes = map[string]int{
	"CONTINUE":                      100,
	// …
} // literal array (−393 tokens)

var ErrorMessages = map[string]string{"…"} // literal array (−127 tokens)

func main() {
	manager := NewLiteralDataManager()
	data := manager.ProcessData()

	fmt.Printf("Tags: %v\n", data.Tags)
	fmt.Printf("Items count: %d\n", len(data.Items))
	fmt.Println(manager.GetLongQuery())
}
