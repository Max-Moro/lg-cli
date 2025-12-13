// Go module for testing literal optimization.
package main

import (
	"fmt"
)

// Short string literal (should be preserved)
const ShortMessage = "Hello, World!"

// Long string literal (candidate for trimming)
const LongMessage = "This is an extremely long message that contains a substantial amount of text content which might be considered…" // literal string (−54 tokens)

// Multi-line string with formatting
const TemplateWithData = `User Information:
- Name: %s
- Email: %s
- Registr…` // literal string (−35 tokens)

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
		smallConfig: map[string]interface{}{
			"debug":   true,
			"version": "1.0.0",
		},
		largeConfig: map[string]interface{}{
			"database": map[string]interface{}{
				"host": "localhost",
				// … (5 more, −107 tokens)
			},
			// … (3 more, −227 tokens)
		},
		supportedLanguages: []string{
			"english",
			"spanish",
			"french",
			"…"
		}, // literal slice (−82 tokens)
		allowedExtensions: []string{
			".go",
			".py",
			".js",
			"…"
		}, // literal slice (−56 tokens)
	}
}

// ProcessData creates a data container with various literals
func (m *LiteralDataManager) ProcessData() *DataContainer {
	smallSlice := []string{"one", "two", "three"}

	largeSlice := []string{
		"item_001",
		"item_002",
		"…"
	} // literal slice (−140 tokens)

	nestedData := map[string]interface{}{
		"level1": map[string]interface{}{
			"level2": map[string]interface{}{
				"level3": map[string]interface{}{
					"data": []map[string]interface{}{
						{"id": 1, "name": "First", "active": true},
						"…"
					} // literal slice (−69 tokens),
					// … (1 more, −57 tokens)
				},
			},
		},
	}

	return &DataContainer{
		Tags:          smallSlice,
		Items:         largeSlice,
		Metadata:      map[string]interface{}{"type": "test", "count": len(smallSlice)},
		Configuration: nestedData,
	}
}

// GetLongQuery returns a very long SQL-like query string
func (m *LiteralDataManager) GetLongQuery() string {
	return `
		SELECT
			users.id, users.username, users.email, users.created_at,
			pro…` // literal string (−173 tokens)
}

// Module-level constants with different sizes
var SmallConstants = struct {
	APIVersion   string
	DefaultLimit int
}{
	APIVersion:   "v1",
	DefaultLimit: 50,
}

var HTTPStatusCodes = map[string]int{
	"CONTINUE":                      100,
	// … (40 more, −317 tokens)
}

var ErrorMessages = map[string]string{
	"VALIDATION_FAILED":      "Input validation failed. Please check your data and try again.",
	// … (6 more, −102 tokens)
}

func main() {
	manager := NewLiteralDataManager()
	data := manager.ProcessData()

	fmt.Printf("Tags: %v\n", data.Tags)
	fmt.Printf("Items count: %d\n", len(data.Items))
	fmt.Println(manager.GetLongQuery())
}
