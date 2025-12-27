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
	"myproject/internal/models"
	"myproject/pkg/utils"
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

// … comment omitted
func (s *PublicService) normalize(u *models.User) *models.User {
	if u == nil {
		return nil
	}
	u.Name = strings.TrimSpace(u.Name)
	u.Email = strings.ToLower(u.Email)
	return u
}

// … comment omitted
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

// … comment omitted
type internalOnly struct {
	data string
}

func (i *internalOnly) doWork() {
	// … comment omitted
}

// … comment omitted
func PublicFunction(name string) string {
	// … comment omitted
	if utils.ToTitle != nil {
		return utils.ToTitle(name)
	}
	return name
}

func privateFunction(data []string) []string {
	// … comment omitted
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
