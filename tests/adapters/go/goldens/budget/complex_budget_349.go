// Comprehensive Go sample for Budget System tests.
// Contains:
// - External imports
// - Local imports
// - Long comments and documentation
// - Big literals (slices/maps/strings)
// - Public vs private API elements
package main


import (
	
)


import (
	
)


import (
	
)

// ModuleTitle is a module level long documentation that might be truncated under tight budgets.
// The text includes several sentences to ensure the comment optimizer has
// something to work with when switching to keep_first_sentence mode.
const ModuleTitle = "Budget System Complex Sample"

const LongText = `This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to
ensu…`

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
	
}

// NewPublicService creates a new service instance
func NewPublicService() *PublicService 


func (s *PublicService) GetUser(id int) *models.User 





func (s *PublicService) Process(list []*models.User) ([]*models.User, error) 






// PublicFunction is an exported function
func PublicFunction(name string) string
