// Comprehensive Go sample for Budget System tests.
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
const ModuleTitle = "Budget System Complex Sample"

const LongText = `This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to
ensu…` // literal string (−15 tokens)

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

// PublicService provides public API operations.
type PublicService struct {
	// … field omitted
}

// NewPublicService creates a new service instance.
func NewPublicService() *PublicService // … function body omitted (5 lines)

// … comment omitted
func (s *PublicService) GetUser(id int) *models.User // … method body omitted (7 lines)

// … comment omitted
// … method omitted

// … comment omitted
func (s *PublicService) Process(list []*models.User) ([]*models.User, error) // … method body omitted (15 lines)

// … comment omitted
// … struct omitted (3 lines)

// … method omitted

// PublicFunction is an exported function.
func PublicFunction(name string) string // … function body omitted (7 lines)

// … 2 functions omitted
