// Comprehensive Go sample for Budget System tests.
// Contains:
// - External imports
// - Local imports
// - Long comments and documentation
// - Big literals (slices/maps/strings)
// - Public vs private API elements
package main

// External imports (most common cases)
import (
	
)

// Third-party imports
import (
	
)

// Local imports (treated as local)
import (
	"myproject/internal/models"
	"myproject/pkg/utils"
)

// ModuleTitle is a module level long documentation that might be truncated under tight budgets.
// The text includes several sentences to ensure the comment optimizer has
// something to work with when switching to keep_first_sentence mode.
const ModuleTitle = "Budget System Complex Sample"

const LongText = `This is an extremely long text that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to
ensure length. This is an extremely long text that is designed to be trimmed.`

var BigObject = map[string]interface{}{
	"users": func() []map[string]interface{} {
		result := make([]map[string]interface{}, 50)
		for i := 0; i < 50; i++ {
			result[i] = map[string]interface{}{
				"id":     i + 1,
				"name":   fmt.Sprintf("User %d", i+1),
				"active": i%2 == 0,
			}
		}
		return result
	}(),
	"config": map[string]interface{}{
		"flags": func() map[string]bool {
			result := make(map[string]bool)
			for i := 0; i < 40; i++ {
				result[fmt.Sprintf("flag_%d", i)] = i%2 == 0
			}
			return result
		}(),
		"thresholds": func() []int {
			result := make([]int, 120)
			for i := 0; i < 120; i++ {
				result[i] = i
			}
			return result
		}(),
	},
}

// PublicService provides public API operations
type PublicService struct {
	cache map[string]*models.User
}

// NewPublicService creates a new service instance
func NewPublicService() *PublicService {
	return &PublicService{
		cache: make(map[string]*models.User),
	}
}

// GetUser is a public API method that gets a user by ID.
// This doc has multiple sentences to allow truncation under budget.
func (s *PublicService) GetUser(id int) *models.User {
	idStr := fmt.Sprintf("%d", id)
	if user, ok := s.cache[idStr]; ok {
		return user
	}
	return nil
}

// normalize is a private helper — should not be visible with public_api_only
func (s *PublicService) normalize(u *models.User) *models.User {
	if u == nil {
		return nil
	}
	u.Name = strings.TrimSpace(u.Name)
	u.Email = strings.ToLower(u.Email)
	return u
}

// Process is a long method body to allow function body stripping
func (s *PublicService) Process(list []*models.User) ([]*models.User, error) {
	if len(list) == 0 {
		return nil, errors.New("empty list")
	}

	out := make([]*models.User, 0, len(list))
	for _, u := range list {
		n := s.normalize(u)
		if n != nil {
			out = append(out, n)
		}
	}

	return out, nil
}

// internalOnly is a private struct — should be filtered out in public_api_only
type internalOnly struct {
	data string
}

func (i *internalOnly) doWork() {
	// noop
}

// PublicFunction is an exported function
func PublicFunction(name string) string {
	// Regular comment that may be stripped
	if utils.ToTitle != nil {
		return utils.ToTitle(name)
	}
	return name
}

func privateFunction(data []string) []string {
	// Not exported; should be removed when public_api_only
	result := make([]string, len(data))
	for i, s := range data {
		result[i] = strings.TrimSpace(s)
	}
	return result
}

func main() {
	svc := NewPublicService()
	user := svc.GetUser(1)
	if user != nil {
		fmt.Println(user)
	}
}
