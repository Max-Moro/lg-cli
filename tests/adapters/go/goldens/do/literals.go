// Go module for testing literal optimization.
package main

import (
	"fmt"
)

// Short string literal (should be preserved)
const ShortMessage = "Hello, World!"

// Long string literal (candidate for trimming)
const LongMessage = "This is an extremely long message that contains a substantial amount of text content which might be considered for trimming when optimizing Go code for AI context windows. The message continues with detailed explanations and verbose descriptions that may not be essential for understanding the core functionality and structure of the code. This string literal spans multiple conceptual lines even though it's defined as a single string literal."

// Multi-line string with formatting
const TemplateWithData = `User Information:
- Name: %s
- Email: %s
- Registration Date: %s
- Account Status: %s
- Permissions: %v
- Last Login: %s
- Profile Completeness: %d%%`

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
				"port": 5432,
				"name": "application_db",
				"ssl":  false,
				"pool": map[string]int{
					"min":                2,
					"max":                10,
					"idleTimeout":        30000,
					"connectionTimeout":  2000,
				},
				"retry": map[string]interface{}{
					"attempts": 3,
					"delay":    1000,
					"backoff":  "exponential",
				},
			},
			"cache": map[string]interface{}{
				"redis": map[string]interface{}{
					"host": "localhost",
					"port": 6379,
					"db":   0,
					"ttl":  3600,
				},
				"memory": map[string]interface{}{
					"maxSize": 1000,
					"ttl":     1800,
				},
			},
			"api": map[string]interface{}{
				"baseUrl": "https://api.example.com",
				"timeout": 30000,
				"retries": 3,
				"rateLimit": map[string]int{
					"requests": 100,
					"window":   60000,
				},
			},
			"features": map[string]bool{
				"authentication": true,
				"authorization":  true,
				"logging":        true,
				"monitoring":     true,
				"analytics":      false,
				"caching":        true,
				"compression":    true,
			},
		},
		supportedLanguages: []string{
			"english", "spanish", "french", "german", "italian", "portuguese",
			"russian", "chinese", "japanese", "korean", "arabic", "hindi",
			"dutch", "swedish", "norwegian", "danish", "finnish", "polish",
			"czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian",
		},
		allowedExtensions: []string{
			".go",
			".py", ".js", ".ts", ".jsx", ".tsx",
			".java", ".kt", ".scala",
			".cpp", ".cxx", ".cc", ".h", ".hpp", ".hxx",
			".cs", ".rs",
			".php", ".rb", ".swift", ".clj",
		},
	}
}

// ProcessData creates a data container with various literals
func (m *LiteralDataManager) ProcessData() *DataContainer {
	smallSlice := []string{"one", "two", "three"}

	largeSlice := []string{
		"item_001", "item_002", "item_003", "item_004", "item_005",
		"item_006", "item_007", "item_008", "item_009", "item_010",
		"item_011", "item_012", "item_013", "item_014", "item_015",
		"item_016", "item_017", "item_018", "item_019", "item_020",
		"item_021", "item_022", "item_023", "item_024", "item_025",
		"item_026", "item_027", "item_028", "item_029", "item_030",
	}

	nestedData := map[string]interface{}{
		"level1": map[string]interface{}{
			"level2": map[string]interface{}{
				"level3": map[string]interface{}{
					"data": []map[string]interface{}{
						{"id": 1, "name": "First", "active": true},
						{"id": 2, "name": "Second", "active": false},
						{"id": 3, "name": "Third", "active": true},
						{"id": 4, "name": "Fourth", "active": true},
						{"id": 5, "name": "Fifth", "active": false},
					},
					"metadata": map[string]interface{}{
						"created":  "2024-01-01",
						"updated":  "2024-01-15",
						"version":  3,
						"checksum": "abcdef123456",
					},
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
			profiles.first_name, profiles.last_name, profiles.bio, profiles.avatar_url,
			addresses.street, addresses.city, addresses.state, addresses.postal_code, addresses.country,
			subscriptions.plan_name, subscriptions.status, subscriptions.expires_at,
			payments.amount, payments.currency, payments.payment_date, payments.method
		FROM users
		LEFT JOIN profiles ON users.id = profiles.user_id
		LEFT JOIN addresses ON users.id = addresses.user_id
		LEFT JOIN subscriptions ON users.id = subscriptions.user_id
		LEFT JOIN payments ON users.id = payments.user_id
		WHERE users.is_active = true
			AND users.email_verified = true
			AND profiles.is_public = true
			AND subscriptions.status IN ('active', 'trial')
		ORDER BY users.created_at DESC, subscriptions.expires_at ASC
		LIMIT 100 OFFSET 0
	`
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
	"SWITCHING_PROTOCOLS":           101,
	"OK":                            200,
	"CREATED":                       201,
	"ACCEPTED":                      202,
	"NON_AUTHORITATIVE_INFORMATION": 203,
	"NO_CONTENT":                    204,
	"RESET_CONTENT":                 205,
	"PARTIAL_CONTENT":               206,
	"MULTIPLE_CHOICES":              300,
	"MOVED_PERMANENTLY":             301,
	"FOUND":                         302,
	"SEE_OTHER":                     303,
	"NOT_MODIFIED":                  304,
	"USE_PROXY":                     305,
	"TEMPORARY_REDIRECT":            307,
	"PERMANENT_REDIRECT":            308,
	"BAD_REQUEST":                   400,
	"UNAUTHORIZED":                  401,
	"PAYMENT_REQUIRED":              402,
	"FORBIDDEN":                     403,
	"NOT_FOUND":                     404,
	"METHOD_NOT_ALLOWED":            405,
	"NOT_ACCEPTABLE":                406,
	"PROXY_AUTHENTICATION_REQUIRED": 407,
	"REQUEST_TIMEOUT":               408,
	"CONFLICT":                      409,
	"GONE":                          410,
	"LENGTH_REQUIRED":               411,
	"PRECONDITION_FAILED":           412,
	"PAYLOAD_TOO_LARGE":             413,
	"URI_TOO_LONG":                  414,
	"UNSUPPORTED_MEDIA_TYPE":        415,
	"RANGE_NOT_SATISFIABLE":         416,
	"EXPECTATION_FAILED":            417,
	"INTERNAL_SERVER_ERROR":         500,
	"NOT_IMPLEMENTED":               501,
	"BAD_GATEWAY":                   502,
	"SERVICE_UNAVAILABLE":           503,
	"GATEWAY_TIMEOUT":               504,
	"HTTP_VERSION_NOT_SUPPORTED":    505,
}

var ErrorMessages = map[string]string{
	"VALIDATION_FAILED":      "Input validation failed. Please check your data and try again.",
	"AUTHENTICATION_REQUIRED": "Authentication is required to access this resource.",
	"AUTHORIZATION_FAILED":   "You do not have permission to perform this action.",
	"RESOURCE_NOT_FOUND":     "The requested resource could not be found on the server.",
	"INTERNAL_ERROR":         "An internal server error occurred. Please try again later.",
	"RATE_LIMIT_EXCEEDED":    "Rate limit exceeded. Please wait before making another request.",
	"INVALID_REQUEST_FORMAT": "The request format is invalid. Please check the documentation.",
}

func main() {
	manager := NewLiteralDataManager()
	data := manager.ProcessData()

	fmt.Printf("Tags: %v\n", data.Tags)
	fmt.Printf("Items count: %d\n", len(data.Items))
	fmt.Println(manager.GetLongQuery())
}
