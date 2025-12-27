// Comprehensive Go sample for Budget System tests.
// Contains:
// - External imports
// - Local imports
// - Long comments and documentation
// - Big literals (slices/maps/strings)
// - Public vs private API elements
package main

// … comment omitted
import (
	// … 3 imports omitted
)

// … comment omitted
import (
	// … import omitted
)

// … comment omitted
import (
	// … 2 imports omitted
)

// ModuleTitle is a module level long documentation that might be truncated under tight budgets.
// The text includes several sentences to ensure the comment optimizer has
// something to work with when switching to keep_first_sentence mode.
const ModuleTitle = "Budget System Complex Sample"

const LongText = `This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to
ensu…` // literal string (−12 tokens)

var BigObject = map[string]interface{}{
	"users": func() []map[string]interface{} {
		result := make([]map[string]interface{}, 50)
		for i := 0; i < 50; i++ {
			result[i] = map[string]interface{}{
				"id":     i + 1,
				// … (2 more, −23 tokens)
			}
		}
		return result
	}(),
	// … (1 more, −128 tokens)
}

// PublicService provides public API operations
type PublicService struct {
	// … field omitted
}

// NewPublicService creates a new service instance
func NewPublicService() *PublicService {
	// … function body omitted (3 lines)
}

// GetUser is a public API method that gets a user by ID.
// This doc has multiple sentences to allow truncation under budget.
func (s *PublicService) GetUser(id int) *models.User {
	// … method body omitted (5 lines)
}

// … method omitted (9 lines)

// … comment omitted
func (s *PublicService) Process(list []*models.User) ([]*models.User, error) {
	// … method body omitted (11 lines)
}

// … struct omitted (4 lines)

// … method omitted (3 lines)

// … comment omitted
func PublicFunction(name string) string {
	// … function body omitted (5 lines)
}

// … 2 functions omitted (15 lines)
