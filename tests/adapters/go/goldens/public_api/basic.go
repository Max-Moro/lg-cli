// Go module for testing public API filtering.
package main

import (
	"fmt"
	"strings"
	"time"
)

// Public module-level constants (should be preserved)
const PublicVersion = "1.0.0"
const APIEndpoint = "https://api.example.com"

// Private module-level constants (should be filtered out)
// … constant omitted

// … variable omitted (7 lines)

// User is a public structure (should be preserved)
type User struct {
	ID        int
	Name      string
	Email     string
	CreatedAt time.Time
}

// internalMetrics is a private structure (should be filtered out)
// … struct omitted (4 lines)

// UserRole is a public type alias (should be preserved)
type UserRole string

const (
	RoleAdmin UserRole = "admin"
	RoleUser  UserRole = "user"
	RoleGuest UserRole = "guest"
)

// internalEventType is a private type (should be filtered out)
// … type omitted

// … constant omitted (5 lines)

// UserManager is a public class with mixed visibility members
type UserManager struct {
	// Public properties
	Version       string
	IsInitialized bool

	// Private properties (should be filtered out with public_api_only)
	// … 3 fields omitted
}

// NewUserManager is a public constructor (should be preserved)
func NewUserManager(apiEndpoint string) *UserManager {
	if apiEndpoint == "" {
		apiEndpoint = APIEndpoint
	}

	manager := &UserManager{
		Version:       PublicVersion,
		IsInitialized: false,
		internalCache: make(map[string]*User),
		metrics:       &internalMetrics{},
		apiEndpoint:   apiEndpoint,
	}

	manager.initialize()
	return manager
}

// CreateUser is a public method (should be preserved)
func (m *UserManager) CreateUser(name, email string) (*User, error) {
	if err := m.validateUserData(name, email); err != nil {
		return nil, err
	}

	user := &User{
		ID:        m.generateID(),
		Name:      name,
		Email:     email,
		CreatedAt: time.Now(),
	}

	m.internalCache[user.Email] = user
	return user, nil
}

// GetUserByID is a public method (should be preserved)
func (m *UserManager) GetUserByID(id int) *User {
	for _, user := range m.internalCache {
		if user.ID == id {
			return user
		}
	}

	return m.fetchUserFromAPI(id)
}

// GetAllUsers is a public method (should be preserved)
func (m *UserManager) GetAllUsers() []*User {
	users := make([]*User, 0, len(m.internalCache))
	for _, user := range m.internalCache {
		users = append(users, user)
	}
	return users
}

// validateUserData is a private method (should be filtered out)
// … method omitted (9 lines)

// generateID is a private method (should be filtered out)
// … method omitted (3 lines)

// isValidEmail is a private method (should be filtered out)
// … method omitted (3 lines)

// fetchUserFromAPI is a private method (should be filtered out)
// … method omitted (4 lines)

// initialize is a private method (should be filtered out)
// … method omitted (3 lines)

// logError is a private method (should be filtered out)
// … method omitted (3 lines)

// ValidateUserRole is a public function (should be preserved)
func ValidateUserRole(role string) bool {
	validRoles := []UserRole{RoleAdmin, RoleUser, RoleGuest}
	for _, r := range validRoles {
		if string(r) == role {
			return true
		}
	}
	return false
}

// CreateDefaultUser is a public function (should be preserved)
func CreateDefaultUser() *User {
	return &User{
		ID:        0,
		Name:      "Default User",
		Email:     "default@example.com",
		CreatedAt: time.Now(),
	}
}

// formatInternalID is a private function (should be filtered out)
// … function omitted (3 lines)

// internalLogger is a private structure (should be filtered out)
// … struct omitted (3 lines)

// newInternalLogger is a private constructor (should be filtered out)
// … function omitted (5 lines)

// log is a private method (should be filtered out)
// … method omitted (4 lines)

// getLogs is a private method (should be filtered out)
// … method omitted (3 lines)

// clearLogs is a private method (should be filtered out)
// … method omitted (3 lines)

// UserUtils is a public namespace-like struct (should be preserved)
type UserUtils struct{}

// FormatUserName is a public method (should be preserved)
func (UserUtils) FormatUserName(user *User) string {
	return fmt.Sprintf("%s (%s)", user.Name, user.Email)
}

// GetUserAge is a public method (should be preserved)
func (UserUtils) GetUserAge(user *User) int64 {
	now := time.Now()
	return int64(now.Sub(user.CreatedAt).Hours() / 24)
}

// internalFormatting is a private function (should be filtered out)
// … function omitted (3 lines)

// InternalUtils is a private namespace-like struct (should be filtered out)
type InternalUtils struct{}

// debugLog is a private method (should be filtered out)
// … method omitted (5 lines)

// measurePerformance is a private method (should be filtered out)
// … method omitted (6 lines)

// … function omitted (7 lines)
