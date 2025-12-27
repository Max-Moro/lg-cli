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

// … constant omitted (2 lines)

// … variable omitted (7 lines)

// User is a public structure (should be preserved)
type User struct {
	ID        int
	Name      string
	Email     string
	CreatedAt time.Time
}

// … struct omitted (5 lines)

// UserRole is a public type alias (should be preserved)
type UserRole string

const (
	RoleAdmin UserRole = "admin"
	RoleUser  UserRole = "user"
	RoleGuest UserRole = "guest"
)

// … type omitted (2 lines)

// … constant omitted (5 lines)

// UserManager is a public class with mixed visibility members
type UserManager struct {
	// Public properties
	Version       string
	IsInitialized bool

	// … 3 fields omitted (4 lines)
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

// … 6 methods omitted (31 lines)

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

// … function omitted (4 lines)

// … struct omitted (4 lines)

// … function omitted (6 lines)

// … 3 methods omitted (13 lines)

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

// … function omitted (4 lines)

// InternalUtils is a private namespace-like struct (should be filtered out)
type InternalUtils struct{}

// … 2 methods omitted (13 lines)

// … function omitted (7 lines)
